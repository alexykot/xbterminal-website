from decimal import Decimal
import logging

from django.db.transaction import atomic
from django.utils import timezone

from bitcoin.rpc import VerifyAlreadyInChainError
from constance import config

from api.utils.urls import get_admin_url
from common.rq_helpers import run_periodic_task, cancel_current_task
from common.db import refresh_for_update
from transactions.constants import (
    COIN_DEC_PLACES,
    COIN_MIN_OUTPUT,
    DEPOSIT_TIMEOUT,
    DEPOSIT_CONFIDENCE_TIMEOUT,
    DEPOSIT_CONFIRMATION_TIMEOUT,
    PAYMENT_TYPES)
from transactions.exceptions import (
    TransactionError,
    DustOutput,
    InvalidTransaction,
    InsufficientFunds,
    InvalidPaymentMessage,
    DoubleSpend,
    TransactionModified,
    RefundError)
from transactions.models import Deposit
from transactions.utils.tx import create_tx
from transactions.utils.bip70 import parse_payment
from transactions.services.bitcoind import BlockChain
from transactions.services.wrappers import get_exchange_rate, is_tx_reliable
from wallet.models import Address
from website.models import Account, Device

logger = logging.getLogger(__name__)


def prepare_deposit(device_or_account, amount):
    """
    Accepts:
        device_or_account: Device or Account instance
        amount: Decimal
    Returns:
        deposit: Deposit instance
    """
    if isinstance(device_or_account, Device):
        device = device_or_account
        account = device.account
    elif isinstance(device_or_account, Account):
        device = None
        account = device_or_account
    if not account.currency.is_enabled:
        raise TransactionError('Account is disabled')
    # Create new address
    deposit_address = Address.create(account.currency.name,
                                     is_change=False)
    # Create model instance
    deposit = Deposit(
        account=account,
        device=device,
        currency=account.merchant.currency,
        amount=amount,
        coin=account.currency,
        deposit_address=deposit_address)
    # Register address
    bc = BlockChain(deposit.coin.name)
    bc.import_address(deposit_address.address, rescan=False)
    # Get exchange rate
    exchange_rate = get_exchange_rate(deposit.currency.name,
                                      deposit.coin.name)
    # Merchant amount
    deposit.merchant_coin_amount = (deposit.amount /
                                    exchange_rate).quantize(COIN_DEC_PLACES)
    if deposit.merchant_coin_amount < COIN_MIN_OUTPUT:
        deposit.merchant_coin_amount = COIN_MIN_OUTPUT
    # Fee
    deposit.fee_coin_amount = (deposit.amount *
                               Decimal(config.OUR_FEE_SHARE) /
                               exchange_rate).quantize(COIN_DEC_PLACES)
    deposit.save()
    # Wait for payment
    run_periodic_task(wait_for_payment, [deposit.pk], interval=2)
    run_periodic_task(check_deposit_status, [deposit.pk], interval=60)
    return deposit


def validate_payment(deposit, transactions, refund_addresses,
                     payment_type):
    """
    Validates payment and saves details to database
    Accepts:
        deposit: Deposit instance
        transactions: list of CTransaction
        refund_addresses: list of addresses
        payment_type: one of PAYMENT_TYPES, integer
    Returns:
        True if deposit status changed to 'received'
        False otherwise
    """
    bc = BlockChain(deposit.coin.name)
    incoming_tx_ids = set()
    received_amount = COIN_DEC_PLACES
    for incoming_tx in transactions:
        # Validate and broadcast TX
        incoming_tx_id = incoming_tx.id()
        if bc.is_tx_valid(incoming_tx):
            try:
                bc.send_raw_transaction(incoming_tx)
            except VerifyAlreadyInChainError:
                logger.warning('transaction already in chain')
                # Already in chain, skip broadcasting
                pass
        else:
            raise InvalidTransaction(incoming_tx_id)
        incoming_tx_ids.add(incoming_tx_id)
        # Get amount
        for output in bc.get_tx_outputs(incoming_tx):
            if output['address'] == deposit.deposit_address.address:
                received_amount += output['amount']
    if payment_type == PAYMENT_TYPES.BIP70 and \
            received_amount < deposit.coin_amount:
        # Throw error for underpaid BIP70 payments
        raise InsufficientFunds

    is_received = False
    # Save deposit details
    with atomic():
        # Ensure that there is no race condition when saving TX IDs
        # and that cancelled deposit will not get received status
        deposit = refresh_for_update(deposit)
        deposit.paid_coin_amount = received_amount
        if refund_addresses:
            deposit.refund_address = refund_addresses[0]
        for incoming_tx_id in incoming_tx_ids:
            if incoming_tx_id not in deposit.incoming_tx_ids:
                deposit.incoming_tx_ids.append(incoming_tx_id)
        if deposit.paid_coin_amount >= deposit.coin_amount and \
                not deposit.time_received and \
                not deposit.time_cancelled:
            # Change status
            deposit.payment_type = payment_type
            deposit.time_received = timezone.now()
            is_received = True
        deposit.save()
        deposit.create_balance_changes()
    return is_received


def handle_bip70_payment(deposit, payment_message):
    """
    Parse and validate BIP70 Payment message
    Accepts:
        deposit: Deposit instance
        payment_message: pb2-encoded message
    Returns:
        payment_ack: pb2-encoded message
    Raises:
        InvalidPaymentMessage
        InvalidTransaction
        InsufficientFunds
    """
    try:
        transactions, refund_addresses, payment_ack = \
            parse_payment(deposit.coin.name, payment_message)
    except Exception as error:
        logger.exception(error)
        raise InvalidPaymentMessage
    # Validate payment
    is_received = validate_payment(deposit, transactions, refund_addresses,
                                   PAYMENT_TYPES.BIP70)
    if is_received:
        run_periodic_task(wait_for_confidence, [deposit.pk], interval=5)
        logger.info('payment received (%s)', deposit.pk)
    return payment_ack


def wait_for_payment(deposit_id):
    """
    Periodic task for monitoring BIP21 payment
    Accepts:
        deposit_id: integer
    """
    deposit = Deposit.objects.get(pk=deposit_id)
    if deposit.time_created + DEPOSIT_TIMEOUT < timezone.now():
        # Timeout, cancel job
        cancel_current_task()
    if deposit.time_received is not None:
        # Payment already validated, cancel job
        cancel_current_task()
        return
    if deposit.time_cancelled is not None:
        # Cancel job, but check deposit address for the last time
        cancel_current_task()
    # Connect to bitcoind
    bc = BlockChain(deposit.coin.name)
    transactions = bc.get_unspent_transactions(deposit.deposit_address.address)
    if transactions:
        if len(transactions) > 1:
            logger.warning('multiple incoming tx')
        # Get refund addresses
        # WARNING: input addresses may be not controlled by the sender
        tx_inputs = bc.get_tx_inputs(transactions[0])
        if len(tx_inputs) > 1:
            logger.warning('incoming tx contains more than one input')
        refund_addresses = [inp['address'] for inp in tx_inputs]
        # Validate payment
        try:
            is_received = validate_payment(
                deposit, transactions, refund_addresses,
                PAYMENT_TYPES.BIP21)
        except Exception as error:
            cancel_current_task()
            logger.exception(error)
        else:
            if is_received:
                cancel_current_task()
                run_periodic_task(wait_for_confidence, [deposit.pk], interval=5)
                logger.info('payment received (%s)', deposit.pk)


def wait_for_confidence(deposit_id):
    """
    Periodic task for monitoring status of incoming transactions
    Accepts:
        deposit_id: Deposit ID, integer
    """
    deposit = Deposit.objects.get(pk=deposit_id)
    if deposit.time_created + DEPOSIT_CONFIDENCE_TIMEOUT < timezone.now():
        # Timeout, cancel job
        cancel_current_task()
    if deposit.time_broadcasted is not None:
        # Confidence threshold reached, cancel job
        cancel_current_task()
        return
    if deposit.time_cancelled is not None:
        # This task could not be started for cancelled deposits
        raise AssertionError
    bc = BlockChain(deposit.coin.name)
    for incoming_tx_id in deposit.incoming_tx_ids:
        try:
            tx_confirmed = bc.is_tx_confirmed(incoming_tx_id, minconf=1)
        except DoubleSpend:
            # Report double spend, cancel job
            logger.error(
                'double spend detected',
                extra={'data': {
                    'deposit_admin_url': get_admin_url(deposit),
                }})
            cancel_current_task()
            return
        except TransactionModified as error:
            # Transaction has been modified (malleability attack)
            logger.warning(
                'transaction has been modified',
                extra={'data': {
                    'deposit_admin_url': get_admin_url(deposit),
                }})
            deposit.incoming_tx_ids = [
                error.another_tx_id if tx_id == incoming_tx_id else tx_id
                for tx_id in deposit.incoming_tx_ids]
            deposit.save()
            break
        if tx_confirmed:
            # Already confirmed, skip confidence check
            continue
        if not is_tx_reliable(incoming_tx_id,
                              deposit.merchant.get_tx_confidence_threshold(),
                              deposit.coin.name):
            # Break cycle, wait for confidence
            break
    else:
        # Update deposit status
        cancel_current_task()
        deposit.time_broadcasted = timezone.now()
        deposit.save()
        if deposit.paid_coin_amount > deposit.coin_amount:
            # Return extra coins to customer
            try:
                refund_deposit(deposit, only_extra=True)
            except RefundError as error:
                logger.exception(error)
        run_periodic_task(wait_for_confirmation, [deposit.pk], interval=30)
        logger.info('payment confidence reached (%s)', deposit.pk)


def wait_for_confirmation(deposit_id):
    """
    Periodic task for confirmation monitoring
    Accepts:
        deposit_id: deposit ID, integer
    """
    deposit = Deposit.objects.get(pk=deposit_id)
    if deposit.time_created + DEPOSIT_CONFIRMATION_TIMEOUT < timezone.now():
        # Timeout, cancel job
        cancel_current_task()
    bc = BlockChain(deposit.coin.name)
    for incoming_tx_id in deposit.incoming_tx_ids:
        try:
            tx_confirmed = bc.is_tx_confirmed(incoming_tx_id)
        except TransactionModified as error:
            # Transaction has been modified (malleability attack)
            logger.warning(
                'transaction has been modified',
                extra={'data': {
                    'deposit_admin_url': get_admin_url(deposit),
                }})
            deposit.incoming_tx_ids = [
                error.another_tx_id if tx_id == incoming_tx_id else tx_id
                for tx_id in deposit.incoming_tx_ids]
            deposit.save()
            return
        if not tx_confirmed:
            # Do not check other transactions
            break
    else:
        cancel_current_task()
        deposit.time_confirmed = timezone.now()
        deposit.save()
        logger.info('payment confirmed (%s)', deposit.pk)


@atomic
def refund_deposit(deposit, only_extra=False):
    """
    Send all money back to customer
    Accepts:
        deposit: Deposit instance
        only_extra: return only extra coins to customer, boolean
            return full amount by default
    """
    # Ensure that refund TX is sent only once
    deposit = refresh_for_update(deposit)
    if not only_extra and deposit.time_notified is not None:
        raise RefundError('User already notified')
    if only_extra and deposit.time_cancelled is not None:
        raise RefundError('Partial refund is not possible for cancelled deposits')
    if deposit.refund_tx_id is not None:
        raise RefundError('Deposit already refunded')
    bc = BlockChain(deposit.coin.name)
    private_key = deposit.deposit_address.get_private_key()
    tx_inputs = []
    tx_amount = COIN_DEC_PLACES
    for output in bc.get_raw_unspent_outputs(deposit.deposit_address.address):
        tx_inputs.append(dict(output, private_key=private_key))
        tx_amount += output['amount']
        if deposit.refund_address is None:
            incoming_tx = bc.get_raw_transaction(output['txid'])
            # WARNING: input addresses may be not controlled by the sender
            deposit.refund_address = bc.get_tx_inputs(incoming_tx)[0]['address']
    if tx_amount == 0:
        raise RefundError('Nothing to refund')
    if only_extra:
        # Send back to customer only extra amount
        tx_amount -= deposit.coin_amount
    tx_fee = bc.get_tx_fee(len(tx_inputs), 2)
    tx_outputs = {}
    tx_outputs[deposit.refund_address] = tx_amount - tx_fee
    if only_extra:
        # Send change to deposit address
        tx_outputs[deposit.deposit_address.address] = deposit.coin_amount
    try:
        refund_tx = create_tx(tx_inputs, tx_outputs)
    except DustOutput:
        raise RefundError('Output is below dust threshold')
    deposit.refund_tx_id = bc.send_raw_transaction(refund_tx)
    deposit.refund_coin_amount = tx_amount
    if not only_extra and deposit.paid_coin_amount != deposit.refund_coin_amount:
        logger.warning('refunding unprocessed payments')
        deposit.paid_coin_amount = deposit.refund_coin_amount
    deposit.save()
    deposit.create_balance_changes()
    logger.warning(
        'payment refunded (%s)',
        deposit.pk,
        extra={'data': {
            'deposit_admin_url': get_admin_url(deposit),
        }})


def check_deposit_status(deposit_id):
    """
    Periodic task for monitoring deposit status
    Accepts:
        deposit_id: deposit ID, integer
    """
    deposit = Deposit.objects.get(pk=deposit_id)
    if deposit.status == 'timeout':
        logger.info('deposit timeout (%s)', deposit.pk)
        cancel_current_task()
    elif deposit.status == 'cancelled' and \
            deposit.time_created + DEPOSIT_TIMEOUT < timezone.now():
        # Stop monitoring of cancelled deposits only after timeout
        try:
            refund_deposit(deposit)
        except RefundError as error:
            if error.message != 'Nothing to refund':
                logger.exception(error)
        cancel_current_task()
    elif deposit.status == 'failed':
        try:
            refund_deposit(deposit)
        except RefundError as error:
            logger.exception(error)
        logger.error(
            'payment failed (%s)',
            deposit.pk,
            extra={'data': {
                'deposit_admin_url': get_admin_url(deposit),
            }})
        cancel_current_task()
    elif deposit.status == 'unconfirmed':
        logger.error(
            'payment not confirmed (%s)',
            deposit.pk,
            extra={'data': {
                'deposit_admin_url': get_admin_url(deposit),
            }})
        cancel_current_task()
    elif deposit.status == 'confirmed':
        cancel_current_task()


def check_deposit_confirmation(deposit):
    """
    Accepts:
        deposit: Deposit instance
    Returns:
        True if all incoming transactions are confirmed, False otherwise
    """
    if deposit.time_confirmed is not None:
        return True
    bc = BlockChain(deposit.coin.name)
    for incoming_tx_id in deposit.incoming_tx_ids:
        if not bc.is_tx_confirmed(incoming_tx_id):
            # Do not check other txs
            break
    else:
        deposit.time_confirmed = timezone.now()
        deposit.save()
        return True
    return False

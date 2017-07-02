from decimal import Decimal
import logging

from django.db.transaction import atomic
from django.utils import timezone

from constance import config

from api.utils.urls import get_admin_url
from common.rq_helpers import run_periodic_task, cancel_current_task
from transactions.constants import (
    BTC_DEC_PLACES,
    BTC_MIN_OUTPUT,
    DEPOSIT_CONFIDENCE_TIMEOUT,
    DEPOSIT_CONFIRMATION_TIMEOUT,
    PAYMENT_TYPES)
from transactions.models import Deposit
from transactions.utils.compat import get_coin_type
from transactions.utils.tx import create_tx_
from operations.exceptions import (
    InsufficientFunds,
    InvalidPaymentMessage,
    DoubleSpend,
    TransactionModified,
    RefundError)
from operations.blockchain import BlockChain
from operations.protocol import parse_payment
from operations.services.wrappers import get_exchange_rate, is_tx_reliable
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
    # Create new address
    coin_type = get_coin_type(account.currency.name)
    deposit_address = Address.create(coin_type, is_change=False)
    # Create model instance
    deposit = Deposit(
        account=account,
        device=device,
        currency=account.merchant.currency,
        amount=amount,
        coin_type=coin_type,
        deposit_address=deposit_address)
    # Register address
    bc = BlockChain(deposit.bitcoin_network)
    bc.import_address(deposit_address.address, rescan=False)
    # Get exchange rate
    exchange_rate = get_exchange_rate(deposit.currency.name)
    # Merchant amount
    deposit.merchant_coin_amount = (deposit.amount /
                                    exchange_rate).quantize(BTC_DEC_PLACES)
    if deposit.merchant_coin_amount < BTC_MIN_OUTPUT:
        deposit.merchant_coin_amount = BTC_MIN_OUTPUT
    # Fee
    deposit.fee_coin_amount = (deposit.amount *
                               Decimal(config.OUR_FEE_SHARE) /
                               exchange_rate).quantize(BTC_DEC_PLACES)
    deposit.save()
    # Wait for payment
    run_periodic_task(wait_for_payment, [deposit.pk], interval=2)
    run_periodic_task(check_deposit_status, [deposit.pk], interval=60)
    return deposit


def validate_payment(deposit, transactions, refund_addresses):
    """
    Validates payment and saves details to database
    Accepts:
        deposit: Deposit instance
        transactions: list of CTransaction
        refund_addresses: list of addresses
    """
    bc = BlockChain(deposit.bitcoin_network)
    incoming_tx_ids = set()
    received_amount = BTC_DEC_PLACES
    for incoming_tx in transactions:
        # Validate and broadcast TX
        incoming_tx_signed = bc.sign_raw_transaction(incoming_tx)
        incoming_tx_id = bc.send_raw_transaction(incoming_tx_signed)
        incoming_tx_ids.add(incoming_tx_id)
        # Get amount
        for output in bc.get_tx_outputs(incoming_tx):
            if str(output['address']) == deposit.deposit_address.address:
                received_amount += output['amount']
    # Save deposit details
    with atomic():
        deposit.refresh_from_db()
        deposit.paid_coin_amount = received_amount
        if refund_addresses:
            deposit.refund_address = refund_addresses[0]
        for incoming_tx_id in incoming_tx_ids:
            if incoming_tx_id not in deposit.incoming_tx_ids:
                deposit.incoming_tx_ids.append(incoming_tx_id)
        deposit.save()
        deposit.create_balance_changes()
    if deposit.status == 'underpaid':
        raise InsufficientFunds


def handle_bip70_payment(deposit, payment_message):
    """
    Parse and validate BIP70 Payment message
    Accepts:
        deposit: Deposit instance
        payment_message: pb2-encoded message
    Returns:
        payment_ack: pb2-encoded message
    """
    try:
        transactions, refund_addresses, payment_ack = \
            parse_payment(payment_message)
    except Exception as error:
        logger.exception(error)
        raise InvalidPaymentMessage
    # Validate payment
    validate_payment(deposit, transactions, refund_addresses)
    # Update status
    if deposit.time_received is None:
        deposit.payment_type = PAYMENT_TYPES.BIP70
        deposit.time_received = timezone.now()
        deposit.save()
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
    if deposit.status == 'timeout':
        # Timeout, cancel job
        cancel_current_task()
    if deposit.time_received is not None:
        # Payment already validated, cancel job
        cancel_current_task()
        return
    if deposit.time_cancelled is not None:
        cancel_current_task()
        return
    # Connect to bitcoind
    bc = BlockChain(deposit.bitcoin_network)
    transactions = bc.get_unspent_transactions(deposit.deposit_address.address)
    if transactions:
        if len(transactions) > 1:
            logger.warning('multiple incoming tx')
        # Get refund addresses
        tx_inputs = bc.get_tx_inputs(transactions[0])
        if len(tx_inputs) > 1:
            logger.warning('incoming tx contains more than one input')
        refund_addresses = [str(inp['address']) for inp in tx_inputs]
        # Validate payment
        try:
            validate_payment(deposit, transactions, refund_addresses)
        except InsufficientFunds:
            # Don't cancel task, wait for next transaction
            pass
        except Exception as error:
            cancel_current_task()
            logger.exception(error)
        else:
            cancel_current_task()
            # Update status and wait for confidence
            if deposit.time_received is None:
                deposit.payment_type = PAYMENT_TYPES.BIP21
                deposit.time_received = timezone.now()
                deposit.save()
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
        cancel_current_task()
        return
    bc = BlockChain(deposit.bitcoin_network)
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
                              deposit.bitcoin_network):
            # Break cycle, wait for confidence
            break
    else:
        cancel_current_task()
        with atomic():
            deposit.refresh_from_db()
            if deposit.time_cancelled is not None:
                # Do not set broadcasted status for cancelled deposits
                return
            deposit.time_broadcasted = timezone.now()
            deposit.save()
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
    bc = BlockChain(deposit.bitcoin_network)
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


def refund_deposit(deposit):
    """
    Send all money back to customer
    Accepts:
        deposit: Deposit instance
    """
    if deposit.time_notified is not None:
        raise RefundError('User already notified')
    if deposit.refund_tx_id is not None:
        raise RefundError('Deposit already refunded')
    if not deposit.refund_address:
        raise RefundError('No refund address')
    bc = BlockChain(deposit.bitcoin_network)
    private_key = deposit.deposit_address.get_private_key()
    tx_inputs = []
    tx_amount = BTC_DEC_PLACES
    for output in bc.get_raw_unspent_outputs(deposit.deposit_address.address):
        tx_inputs.append(dict(output, private_key=private_key))
        tx_amount += output['amount']
    if tx_amount == 0:
        raise RefundError('Nothing to refund')
    tx_fee = bc.get_tx_fee(1, 1)
    if tx_amount - tx_fee < BTC_MIN_OUTPUT:
        raise RefundError('Output is below dust threshold')
    tx_outputs = {deposit.refund_address: tx_amount - tx_fee}
    refund_tx = create_tx_(tx_inputs, tx_outputs)
    deposit.refund_tx_id = bc.send_raw_transaction(refund_tx)
    deposit.refund_coin_amount = tx_amount
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
    if deposit.status in ['timeout', 'cancelled']:
        try:
            refund_deposit(deposit)
        except RefundError:
            pass
        cancel_current_task()
    elif deposit.status == 'failed':
        try:
            refund_deposit(deposit)
        except RefundError:
            pass
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

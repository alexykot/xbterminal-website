from decimal import Decimal
import logging

from constance import config
from django.utils import timezone

from operations import (
    BTC_DEC_PLACES,
    BTC_MIN_OUTPUT,
    WITHDRAWAL_TIMEOUT,
    WITHDRAWAL_BROADCAST_TIMEOUT,
    WITHDRAWAL_CONFIRMATION_TIMEOUT,
    instantfiat)
from operations.services.wrappers import get_exchange_rate, is_tx_reliable
from operations.blockchain import (
    BlockChain,
    validate_bitcoin_address,
    serialize_outputs,
    deserialize_outputs)
from operations.models import WithdrawalOrder
from operations.exceptions import (
    WithdrawalError,
    InsufficientFunds,
    DoubleSpend,
    TransactionModified)
from website.models import Device, Account
from website.utils.accounts import create_account_txs
from api.utils.urls import get_admin_url
from common.rq_helpers import cancel_current_task, run_periodic_task

logger = logging.getLogger(__name__)


def _get_all_reserved_outputs(current_order):
    """
    Get all outputs reserved by active orders, excluding current order
    Accepts:
        current_order: WithdrawalOrder instance
    Returns:
        set of COutPoint instances
    """
    # Active orders == withdrawal orders with status 'new'
    active_orders = WithdrawalOrder.objects.\
        exclude(pk=current_order.pk).\
        filter(
            account=current_order.account,
            time_created__gt=timezone.now() - WITHDRAWAL_TIMEOUT,
            time_cancelled__isnull=True)
    all_reserved_outputs = set()  # COutPoint is hashable
    for order in active_orders:
        all_reserved_outputs.update(
            deserialize_outputs(order.reserved_outputs))
    return all_reserved_outputs


def prepare_withdrawal(device_or_account, fiat_amount):
    """
    Check merchant's account balance, create withdrawal order
    Accepts:
        device_or_account: Device or Account instance
        fiat_amount: Decimal
    Returns:
        order: WithdrawalOrder instance
    """
    if isinstance(device_or_account, Device):
        device = device_or_account
        account = device.account
    elif isinstance(device_or_account, Account):
        device = None
        account = device_or_account
    if not account:
        raise WithdrawalError('Account is not set for device.')
    if account.instantfiat and \
            account.merchant.currency != account.currency:
        raise WithdrawalError(
            'Account currency should match merchant currency.')
    if not account.instantfiat and account.address_set.count() == 0:
        raise WithdrawalError('Nothing to withdraw.')
    if device is not None and fiat_amount > device.max_payout:
        raise WithdrawalError(
            'Amount exceeds max payout for current device.')

    # TODO: fiat currency -> currency
    order = WithdrawalOrder(
        device=device,
        account=account,
        bitcoin_network=account.bitcoin_network,
        fiat_currency=account.merchant.currency,
        fiat_amount=fiat_amount,
        tx_fee_btc_amount=BTC_DEC_PLACES)
    # Calculate BTC amount
    # WARNING: exchange rate and BTC amount will change
    # for instantfiat withdrawals after confirmation
    order.exchange_rate = get_exchange_rate(order.fiat_currency.name).\
        quantize(BTC_DEC_PLACES)
    order.customer_btc_amount = (order.fiat_amount / order.exchange_rate).\
        quantize(BTC_DEC_PLACES)
    if order.customer_btc_amount < BTC_MIN_OUTPUT:
        raise WithdrawalError('Customer BTC amount is below dust threshold')

    if not account.instantfiat:
        # Find unspent outputs which are not reserved by other orders
        # and check balance
        bc = BlockChain(order.bitcoin_network)
        minconf = 0 if config.WITHDRAW_UNCONFIRMED else 1
        all_reserved_outputs = _get_all_reserved_outputs(order)
        reserved_outputs = []
        reserved_sum = Decimal(0)
        # Look for unspent outputs on account addresses (in reverse order)
        for address in account.address_set.order_by('-created_at'):
            unspent_outputs = bc.get_unspent_outputs(address.address,
                                                     minconf=minconf)
            for output in unspent_outputs:
                if output['outpoint'] in all_reserved_outputs:
                    # Output already reserved by another order, skip
                    continue
                reserved_sum += output['amount']
                reserved_outputs.append(output['outpoint'])
                order.tx_fee_btc_amount = bc.get_tx_fee(len(reserved_outputs), 2)
                if reserved_sum >= order.btc_amount:
                    break
            if reserved_sum >= order.btc_amount:
                break
        if reserved_sum < order.btc_amount:
            logger.error(
                'Withdrawal error - insufficient funds',
                extra={'data': {
                    'account_id': account.pk,
                    'account_admin_url': get_admin_url(account),
                }})
            raise WithdrawalError('Insufficient funds.')
        order.reserved_outputs = serialize_outputs(reserved_outputs)
        logger.info('reserved {0} unspent outputs'.format(
            len(reserved_outputs)))

        # Calculate change amount
        order.change_btc_amount = reserved_sum - order.btc_amount
        if order.change_btc_amount < BTC_MIN_OUTPUT:
            order.customer_btc_amount += order.change_btc_amount
            order.change_btc_amount = BTC_DEC_PLACES
    else:
        # Check confirmed balance of instantfiat account
        # TODO: improve calculation of balance_confirmed
        if account.balance_confirmed < order.fiat_amount:
            logger.error(
                'Withdrawal error - insufficient funds',
                extra={'data': {
                    'account_id': account.pk,
                    'account_admin_url': get_admin_url(account),
                }})
            raise WithdrawalError('Insufficient funds.')
        order.tx_fee_btc_amount = BTC_DEC_PLACES
        order.change_btc_amount = BTC_DEC_PLACES

    order.save()
    return order


def send_transaction(order, customer_address):
    """
    Accepts:
        order: withdrawal order instance
        customer_address: valid bitcoin address
    """
    # Validate customer address
    error_message = validate_bitcoin_address(customer_address,
                                             order.bitcoin_network)
    if error_message:
        raise WithdrawalError(error_message)
    else:
        order.customer_address = customer_address

    if not order.account.instantfiat:
        # Get reserved outputs and check them again
        tx_inputs = deserialize_outputs(order.reserved_outputs)
        all_reserved_outputs = _get_all_reserved_outputs(order)
        if set(tx_inputs) & all_reserved_outputs:
            # Some of the reserved outputs are reserved by other orders
            logger.error(
                'Withdrawal error - some outputs are reserved by other orders',
                extra={'data': {
                    'order_uid': order.uid,
                    'order_admin_url': get_admin_url(order),
                }})
            raise WithdrawalError('Insufficient funds.')
        # Create and send transaction
        change_address = order.account.address_set.first().address
        tx_outputs = {
            order.customer_address: order.customer_btc_amount,
            change_address: order.change_btc_amount,
        }
        bc = BlockChain(order.bitcoin_network)
        tx = bc.create_raw_transaction(tx_inputs, tx_outputs)
        tx_signed = bc.sign_raw_transaction(tx)
        order.outgoing_tx_id = bc.send_raw_transaction(tx_signed)
        order.time_sent = timezone.now()
    else:
        try:
            # TODO: only one identifier is needed
            (order.instantfiat_transfer_id,
             order.instantfiat_reference,
             order.customer_btc_amount) = instantfiat.send_transaction(
                order.account,
                order.fiat_amount,
                order.customer_address)
        except InsufficientFunds:
            logger.error(
                'Withdrawal error - insufficient funds',
                extra={'data': {
                    'account_id': order.account.pk,
                    'account_admin_url': get_admin_url(order.account),
                    'order_uid': order.uid,
                }})
            raise WithdrawalError('Insufficient funds.')
        except:
            raise WithdrawalError('Instantfiat error.')
        # Don't set time_sent at this moment

    order.save()
    # Update account balance
    create_account_txs(order)

    if not order.account.instantfiat:
        run_periodic_task(wait_for_confidence, [order.uid], interval=5)
    else:
        run_periodic_task(wait_for_processor, [order.uid], interval=5)


def wait_for_confidence(order_uid):
    """
    Asynchronous task
    Accepts:
        order_uid: WithdrawalOrder unique identifier
    """
    try:
        order = WithdrawalOrder.objects.get(uid=order_uid)
    except WithdrawalOrder.DoesNotExist:
        # WithdrawalOrder deleted, cancel job
        cancel_current_task()
        return
    if order.time_created + WITHDRAWAL_BROADCAST_TIMEOUT < timezone.now():
        # Timeout, cancel job
        logger.error(
            'Withdrawal error - confidence not reached',
            extra={'data': {
                'order_uid': order.uid,
                'order_admin_url': get_admin_url(order),
            }})
        cancel_current_task()
        return
    bc = BlockChain(order.bitcoin_network)
    # If transaction is already confirmed, skip confidence check
    if bc.is_tx_confirmed(order.outgoing_tx_id, minconf=1) or \
            is_tx_reliable(order.outgoing_tx_id, order.bitcoin_network):
        cancel_current_task()
        if order.time_broadcasted is None:
            order.time_broadcasted = timezone.now()
            order.save()
            run_periodic_task(wait_for_confirmation, [order.uid],
                              interval=15)


def wait_for_processor(order_uid):
    """
    Asynchronous task
    Accepts:
        order_uid: WithdrawalOrder unique identifier
    """
    try:
        order = WithdrawalOrder.objects.get(uid=order_uid)
    except WithdrawalOrder.DoesNotExist:
        # WithdrawalOrder deleted, cancel job
        cancel_current_task()
        return
    if order.time_created + WITHDRAWAL_BROADCAST_TIMEOUT < timezone.now():
        # Timeout, cancel job
        logger.error(
            'Withdrawal error - instantfiat timeout',
            extra={'data': {
                'order_uid': order.uid,
                'order_admin_url': get_admin_url(order),
            }})
        cancel_current_task()
        return
    try:
        is_completed, outgoing_tx_id = instantfiat.check_transfer(
            order.account,
            order.instantfiat_transfer_id)
    except Exception as error:
        logger.exception(error)
        return
    if is_completed:
        cancel_current_task()
        order.outgoing_tx_id = outgoing_tx_id
        order.time_sent = timezone.now()
        # TODO: check for confidence in another task?
        order.time_broadcasted = timezone.now()
        order.save()
        run_periodic_task(wait_for_confirmation, [order.uid], interval=30)


def wait_for_confirmation(order_uid):
    """
    Asynchronous task
    Accepts:
        order_uid: WithdrawalOrder unique identifier
    """
    try:
        order = WithdrawalOrder.objects.get(uid=order_uid)
    except WithdrawalOrder.DoesNotExist:
        # WithdrawalOrder deleted, cancel job
        cancel_current_task()
        return
    if order.time_created + WITHDRAWAL_CONFIRMATION_TIMEOUT < timezone.now():
        # Timeout, cancel job
        cancel_current_task()
    bc = BlockChain(order.bitcoin_network)
    try:
        tx_confirmed = bc.is_tx_confirmed(order.outgoing_tx_id)
    except DoubleSpend:
        # Report double spend, cancel job
        logger.error(
            'double spend detected',
            extra={'data': {
                'order_uid': order.uid,
                'order_admin_url': get_admin_url(order),
            }})
        cancel_current_task()
        return
    except TransactionModified as error:
        logger.warning(
            'transaction has been modified',
            extra={'data': {
                'order_uid': order.uid,
                'order_admin_url': get_admin_url(order),
            }})
        order.outgoing_tx_id = error.another_tx_id
        order.save()
        return
    if tx_confirmed:
        cancel_current_task()
        if order.time_confirmed is None:
            order.time_confirmed = timezone.now()
            order.save()

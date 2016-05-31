from decimal import Decimal
import logging

from constance import config
from django.utils import timezone

from operations import (
    BTC_DEC_PLACES,
    BTC_MIN_OUTPUT,
    WITHDRAWAL_TIMEOUT,
    WITHDRAWAL_BROADCAST_TIMEOUT,
    instantfiat)
from operations.services.wrappers import get_exchange_rate, is_tx_reliable
from operations.blockchain import (
    BlockChain,
    get_tx_fee,
    validate_bitcoin_address,
    serialize_outputs,
    deserialize_outputs)
from operations.rq_helpers import cancel_current_task, run_periodic_task
from operations.models import WithdrawalOrder
from operations.exceptions import WithdrawalError
from website.utils.accounts import create_account_txs
from website.utils.email import send_error_message

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
            merchant_address=current_order.merchant_address,
            time_created__gt=timezone.now() - WITHDRAWAL_TIMEOUT,
            time_cancelled__isnull=True)
    all_reserved_outputs = set()  # COutPoint is hashable
    for order in active_orders:
        all_reserved_outputs.update(
            deserialize_outputs(order.reserved_outputs))
    return all_reserved_outputs


def prepare_withdrawal(device, fiat_amount):
    """
    Check merchant's account balance, create withdrawal order
    Accepts:
        device: Device instance
        fiat_amount: Decimal
    Returns:
        order: WithdrawalOrder instance
    """
    if not device.account:
        raise WithdrawalError('Account is not set for device.')
    if device.account.instantfiat and \
            device.merchant.currency != device.account.currency:
        raise WithdrawalError(
            'Account currency should match merchant currency.')
    if not device.account.instantfiat and not device.account.bitcoin_address:
        raise WithdrawalError('Nothing to withdraw.')

    # TODO: fiat currency -> currency
    order = WithdrawalOrder(
        device=device,
        bitcoin_network=device.bitcoin_network,
        fiat_currency=device.merchant.currency,
        fiat_amount=fiat_amount)
    # Calculate BTC amount
    # WARNING: exchange rate and BTC amount will change
    # for instantfiat withdrawals after confirmation
    order.exchange_rate = get_exchange_rate(order.fiat_currency.name).\
        quantize(BTC_DEC_PLACES)
    order.customer_btc_amount = (order.fiat_amount / order.exchange_rate).\
        quantize(BTC_DEC_PLACES)
    if order.customer_btc_amount < BTC_MIN_OUTPUT:
        raise WithdrawalError('Customer BTC amount is below dust threshold')

    if not order.device.account.instantfiat:
        order.merchant_address = device.account.bitcoin_address
        # Find unspent outputs which are not reserved by other orders
        # and check balance
        bc = BlockChain(order.bitcoin_network)
        minconf = 0 if config.WITHDRAW_UNCONFIRMED else 1
        unspent_sum = Decimal(0)
        unspent_outputs = bc.get_unspent_outputs(order.merchant_address,
                                                 minconf=minconf)
        all_reserved_outputs = _get_all_reserved_outputs(order)
        reserved_outputs = []
        for output in unspent_outputs:
            if output['outpoint'] in all_reserved_outputs:
                # Output already reserved by another order, skip
                continue
            unspent_sum += output['amount']
            reserved_outputs.append(output['outpoint'])
            order.tx_fee_btc_amount = get_tx_fee(len(reserved_outputs), 2)
            if unspent_sum >= order.btc_amount:
                break
        else:
            logger.error('insufficient funds',
                         extra={'data': {'account': str(device.account)}})
            raise WithdrawalError('Insufficient funds')
        order.reserved_outputs = serialize_outputs(reserved_outputs)
        logger.info('reserved {0} of {1} unspent outputs'.format(
            len(reserved_outputs), len(unspent_outputs)))

        # Calculate change amount
        order.change_btc_amount = unspent_sum - order.btc_amount
        if order.change_btc_amount < BTC_MIN_OUTPUT:
            order.customer_btc_amount += order.change_btc_amount
            order.change_btc_amount = BTC_DEC_PLACES
    else:
        # Check confirmed balance of instantfiat account
        # TODO: improve calculation of balance_confirmed
        if order.device.account.balance_confirmed < order.fiat_amount:
            logger.error('insufficient funds',
                         extra={'data': {'account': str(device.account)}})
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

    if not order.device.account.instantfiat:
        # Get reserved outputs and check them again
        tx_inputs = deserialize_outputs(order.reserved_outputs)
        all_reserved_outputs = _get_all_reserved_outputs(order)
        if set(tx_inputs) & all_reserved_outputs:
            # Some of the reserved outputs are reserved by other orders
            logger.critical('send_transaction - some outputs are reserved by other orders')
            raise WithdrawalError('Insufficient funds')
        # Create and send transaction
        tx_outputs = {
            order.customer_address: order.customer_btc_amount,
            order.merchant_address: order.change_btc_amount,
        }
        bc = BlockChain(order.bitcoin_network)
        tx = bc.create_raw_transaction(tx_inputs, tx_outputs)
        tx_signed = bc.sign_raw_transaction(tx)
        order.outgoing_tx_id = bc.send_raw_transaction(tx_signed)
        order.time_sent = timezone.now()
    else:
        try:
            # TODO: find transaction ID and save to outgoing_tx_id field
            # TODO: only one identifier is needed
            (order.instantfiat_transfer_id,
             order.instantfiat_reference,
             order.customer_btc_amount) = instantfiat.send_transaction(
                order.device.account,
                order.fiat_amount,
                order.customer_address)
        except:
            # TODO: better error handling
            raise WithdrawalError('Instantfiat error.')
        # Don't set time_sent at this moment

    order.save()
    # Update account balance
    create_account_txs(order)

    if not order.device.account.instantfiat:
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
        send_error_message(order=order)
        cancel_current_task()
        return
    if is_tx_reliable(order.outgoing_tx_id, order.bitcoin_network):
        cancel_current_task()
        if order.time_broadcasted is None:
            order.time_broadcasted = timezone.now()
            order.save()


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
        # WARNING: order status is 'timeout', not 'failed'
        send_error_message(order=order)
        cancel_current_task()
        return
    if instantfiat.is_transfer_completed(
            order.device.account,
            order.instantfiat_transfer_id):
        cancel_current_task()
        order.time_sent = timezone.now()
        # TODO: check for confidence in another task?
        order.time_broadcasted = timezone.now()
        order.save()

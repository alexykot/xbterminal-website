import datetime
from decimal import Decimal
from django.utils import timezone

from payment import blockr, BTC_DEC_PLACES, BTC_MIN_OUTPUT
from payment.average import get_exchange_rate
from payment.blockchain import (
    BlockChain,
    get_tx_fee,
    validate_bitcoin_address,
    serialize_outputs,
    deserialize_outputs)
from payment.tasks import cancel_current_task, run_periodic_task
from website.models import BTCAccount, WithdrawalOrder


class WithdrawalError(Exception):

    def __init__(self, message):
        super(WithdrawalError, self).__init__()
        self.message = message


def prepare_withdrawal(device, fiat_amount):
    """
    Check merchant's account balance, create withdrawal order
    Accepts:
        device: Device instance
        fiat_amount: Decimal
    Returns:
        order: WithdrawalOrder instance
    """
    try:
        account = BTCAccount.objects.get(merchant=device.merchant,
                                         network=device.bitcoin_network,
                                         address__isnull=False)
    except BTCAccount.DoesNotExist:
        raise WithdrawalError('Merchant doesn\'t have BTC account for {0}'.format(
            device.bitcoin_network))

    order = WithdrawalOrder(
        device=device,
        bitcoin_network=device.bitcoin_network,
        merchant_address=account.address,
        fiat_currency=device.merchant.currency,
        fiat_amount=fiat_amount)
    # Calculate BTC amount
    order.exchange_rate = get_exchange_rate(order.fiat_currency.name).\
        quantize(BTC_DEC_PLACES)
    order.customer_btc_amount = (order.fiat_amount / order.exchange_rate).\
        quantize(BTC_DEC_PLACES)
    if order.customer_btc_amount < BTC_MIN_OUTPUT:
        raise WithdrawalError('Customer BTC amount is below dust threshold')

    # Get unspent outputs and check balance
    bc = BlockChain(order.bitcoin_network)
    reserved_outputs = []
    unspent_sum = Decimal(0)
    for output in bc.get_unspent_outputs(order.merchant_address):
        unspent_sum += output['amount']
        reserved_outputs.append(output['outpoint'])
        order.tx_fee_btc_amount = get_tx_fee(len(reserved_outputs), 2)
        if unspent_sum >= order.btc_amount:
            break
    else:
        raise WithdrawalError('Insufficient funds')
    order.reserved_outputs = serialize_outputs(reserved_outputs)
    # Calculate change amount
    order.change_btc_amount = unspent_sum - order.btc_amount
    if order.change_btc_amount < BTC_MIN_OUTPUT:
        order.customer_btc_amount += order.change_btc_amount
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

    # Send transaction
    tx_inputs = deserialize_outputs(order.reserved_outputs)
    tx_outputs = {
        order.customer_address: order.customer_btc_amount,
        order.merchant_address: order.change_btc_amount,
    }
    bc = BlockChain(order.bitcoin_network)
    tx = bc.create_raw_transaction(tx_inputs, tx_outputs)
    tx_signed = bc.sign_raw_transaction(tx)
    order.outgoing_tx_id = bc.send_raw_transaction(tx_signed)
    order.time_sent = timezone.now()
    order.save()
    run_periodic_task(wait_for_broadcast, [order.uid], interval=5)


def wait_for_broadcast(order_uid):
    """
    Asynchronous task
    Accepts:
        order_uid: WithdrawalOrder unique identifier
    """
    try:
        order = WithdrawalOrder.objects.get(uid=order_uid)
    except WithdrawalOrder.DoesNotExist:
        # PaymentOrder deleted, cancel job
        cancel_current_task()
        return
    if order.time_created + datetime.timedelta(minutes=45) < timezone.now():
        # Timeout, cancel job
        cancel_current_task()
    if blockr.is_tx_broadcasted(order.outgoing_tx_id,
                                order.device.bitcoin_network):
        cancel_current_task()
        if order.time_broadcasted is None:
            order.time_broadcasted = timezone.now()
            order.save()

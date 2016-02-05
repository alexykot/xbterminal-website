"""
Payment operations
"""
from decimal import Decimal
import logging

from bitcoin.rpc import JSONRPCException
from bitcoin.wallet import CBitcoinAddress

from django.utils import timezone
from constance import config

from operations import (
    FIAT_DEC_PLACES,
    FIAT_MIN_OUTPUT,
    BTC_DEC_PLACES,
    BTC_MIN_OUTPUT,
    PAYMENT_TIMEOUT,
    PAYMENT_VALIDATION_TIMEOUT,
    PAYMENT_EXCHANGE_TIMEOUT,
    PAYMENT_CONFIRMATION_TIMEOUT,
    blockchain,
    instantfiat,
    exceptions,
    protocol)
from operations.services import blockcypher
from operations.services.price import get_exchange_rate
from operations.rq_helpers import run_periodic_task, cancel_current_task
from operations.models import PaymentOrder

from website.models import BTCAccount
from website.utils import send_error_message

logger = logging.getLogger(__name__)


def prepare_payment(device, fiat_amount):
    """
    Accepts:
        device: website.models.Device
        amount_fiat: Decimal
    Returns:
        payment_order: PaymentOrder instance
    """
    details = {
        'bitcoin_network': None,
        'local_address': None,
        'merchant_address': None,
        'fee_address': None,
        'instantfiat_address': None,
        'fiat_currency': None,
        'fiat_amount': FIAT_DEC_PLACES,
        'instantfiat_fiat_amount': FIAT_DEC_PLACES,
        'instantfiat_btc_amount': BTC_DEC_PLACES,
        'merchant_btc_amount': BTC_DEC_PLACES,
        'fee_btc_amount': BTC_DEC_PLACES,
        'tx_fee_btc_amount': BTC_DEC_PLACES,
        'btc_amount': BTC_DEC_PLACES,
        'effective_exchange_rate': None,
        'instantfiat_invoice_id': None,
    }
    # Connect to bitcoind
    bc = blockchain.BlockChain(device.bitcoin_network)
    details['bitcoin_network'] = device.bitcoin_network
    # Addresses
    try:
        details['local_address'] = str(bc.get_new_address())
    except Exception as error:
        logger.exception(error)
        raise exceptions.NetworkError
    details['merchant_address'] = device.bitcoin_address
    details['fee_address'] = device.our_fee_address
    # Exchange service
    details['fiat_currency'] = device.merchant.currency
    details['fiat_amount'] = fiat_amount.quantize(FIAT_DEC_PLACES)
    assert details['fiat_amount'] >= FIAT_MIN_OUTPUT
    details['instantfiat_fiat_amount'] = (details['fiat_amount'] *
                                          Decimal(device.percent / 100)
                                          ).quantize(FIAT_DEC_PLACES)
    if details['instantfiat_fiat_amount'] >= FIAT_MIN_OUTPUT:
        instantfiat_data = instantfiat.create_invoice(
            device.merchant,
            details['instantfiat_fiat_amount'])
        details.update(instantfiat_data)
        assert details['instantfiat_btc_amount'] > 0
        if details['instantfiat_btc_amount'] < BTC_MIN_OUTPUT:
            details['instantfiat_btc_amount'] = BTC_MIN_OUTPUT
        exchange_rate = details['instantfiat_fiat_amount'] / details['instantfiat_btc_amount']
    else:
        details['instantfiat_fiat_amount'] = FIAT_DEC_PLACES
        exchange_rate = get_exchange_rate(details['fiat_currency'].name)
    # Validate addresses
    for address_field in ['local_address', 'merchant_address',
                          'fee_address', 'instantfiat_address']:
        address = details[address_field]
        if address:
            error_message = blockchain.validate_bitcoin_address(
                address, device.bitcoin_network)
        assert error_message is None
    # Fee
    details['fee_btc_amount'] = (details['fiat_amount'] *
                                 Decimal(config.OUR_FEE_SHARE) /
                                 exchange_rate).quantize(BTC_DEC_PLACES)
    if details['fee_btc_amount'] < BTC_MIN_OUTPUT:
        details['fee_btc_amount'] = BTC_DEC_PLACES
    # Merchant
    details['merchant_btc_amount'] = ((details['fiat_amount'] - details['instantfiat_fiat_amount']) /
                                      exchange_rate).quantize(BTC_DEC_PLACES)
    assert details['merchant_btc_amount'] >= 0
    if 0 < details['merchant_btc_amount'] < BTC_MIN_OUTPUT:
        details['merchant_btc_amount'] = BTC_MIN_OUTPUT
    # TX fee
    details['tx_fee_btc_amount'] = blockchain.get_tx_fee(1, 3)
    # Total
    details['btc_amount'] = (details['merchant_btc_amount'] +
                             details['instantfiat_btc_amount'] +
                             details['fee_btc_amount'] +
                             details['tx_fee_btc_amount'])
    # Prepare payment order
    payment_order = PaymentOrder(
        device=device,
        **details)
    payment_order.save()
    # Schedule tasks
    run_periodic_task(wait_for_payment, [payment_order.uid])
    run_periodic_task(wait_for_validation, [payment_order.uid])
    run_periodic_task(check_payment_status, [payment_order.uid], interval=60)
    return payment_order


def wait_for_payment(payment_order_uid):
    """
    Asynchronous task
    Accepts:
        payment_order_uid: PaymentOrder unique identifier
    """
    # Check current balance
    try:
        payment_order = PaymentOrder.objects.get(uid=payment_order_uid)
    except PaymentOrder.DoesNotExist:
        # PaymentOrder deleted, cancel job
        cancel_current_task()
        return
    if payment_order.time_created + PAYMENT_TIMEOUT < timezone.now():
        # Timeout, cancel job
        cancel_current_task()
    if payment_order.incoming_tx_id is not None:
        # Payment already validated, cancel job
        cancel_current_task()
        return
    # Connect to bitcoind
    bc = blockchain.BlockChain(payment_order.device.bitcoin_network)
    transactions = bc.get_unspent_transactions(
        CBitcoinAddress(payment_order.local_address))
    if transactions:
        try:
            validate_payment(payment_order, transactions, 'bip0021')
        except exceptions.InsufficientFunds:
            reverse_payment(payment_order, close_order=False)
            # Don't cancel task, wait for next transaction
        else:
            cancel_current_task()


def parse_payment(payment_order, payment_message):
    """
    Parse and validate BIP0070 Payment message
    Accepts:
        payment_order: PaymentOrder instance
        payment_message: pb2-encoded message
    Returns:
        payment_ack: pb2-encoded message
    """
    # Select network
    bc = blockchain.BlockChain(payment_order.device.bitcoin_network)
    try:
        (transactions,
         refund_addresses,
         payment_ack) = protocol.parse_payment(payment_message)
    except Exception as error:
        raise exceptions.InvalidPaymentMessage
    validate_payment(payment_order, transactions, 'bip0070')
    if refund_addresses:
        payment_order.refund_address = refund_addresses[0]
        payment_order.save()
    return payment_ack


def validate_payment(payment_order, transactions, payment_type):
    """
    Validates payment and stores incoming transaction id
    in PaymentOrder instance
    Accepts:
        payment_order: PaymentOrder instance
        transactions: list of CTransaction
        payment_type: bip0021 or bip0070
    """
    assert payment_type in ['bip0021', 'bip0070']
    bc = blockchain.BlockChain(payment_order.device.bitcoin_network)
    if len(transactions) != 1:
        raise exceptions.PaymentError('Expecting single transaction')
    incoming_tx = transactions[0]
    # Validate transaction
    incoming_tx_signed = bc.sign_raw_transaction(incoming_tx)
    # Save refund address (BIP0021)
    if payment_type == 'bip0021':
        payment_order.refund_address = str(bc.get_tx_inputs(incoming_tx)[0]['address'])
    # Check amount
    btc_amount = BTC_DEC_PLACES
    for output in bc.get_tx_outputs(incoming_tx):
        if str(output['address']) == payment_order.local_address:
            btc_amount += output['amount']
    if btc_amount < payment_order.btc_amount:
        raise exceptions.InsufficientFunds
    # Broadcast transaction (BIP0070)
    if payment_type == 'bip0070':
        try:
            bc.send_raw_transaction(incoming_tx_signed)
        except JSONRPCException as error:
            logger.exception(error)
    # Save incoming transaction id
    payment_order.incoming_tx_id = blockchain.get_txid(incoming_tx)
    payment_order.payment_type = payment_type
    payment_order.time_recieved = timezone.now()
    payment_order.save()
    logger.info('payment recieved ({0})'.format(payment_order.uid))


def reverse_payment(order, close_order=True):
    """
    Send all money back to customer
    Accepts:
        order: PaymentOrder instance
        close_order: whether to write time_refunded or not, boolean
    """
    bc = blockchain.BlockChain(order.bitcoin_network)
    tx_inputs = []
    amount = BTC_DEC_PLACES
    for output in bc.get_unspent_outputs(order.local_address):
        tx_inputs.append(output['outpoint'])
        amount += output['amount']
    amount -= blockchain.get_tx_fee(1, 1)
    tx_outputs = {order.refund_address: amount}
    refund_tx = bc.create_raw_transaction(tx_inputs, tx_outputs)
    refund_tx_signed = bc.sign_raw_transaction(refund_tx)
    bc.send_raw_transaction(refund_tx_signed)
    if close_order:
        # Changing order status, customer should be notified
        order.refund_tx_id = blockchain.get_txid(refund_tx)
        order.time_refunded = timezone.now()
        order.save()
    logger.warning('payment returned ({0})'.format(order.uid))


def wait_for_validation(payment_order_uid):
    """
    Asynchronous task
    Accepts:
        payment_order_uid: PaymentOrder unique identifier
    """
    try:
        payment_order = PaymentOrder.objects.get(uid=payment_order_uid)
    except PaymentOrder.DoesNotExist:
        # PaymentOrder deleted, cancel job
        cancel_current_task()
        return
    if payment_order.time_created + PAYMENT_VALIDATION_TIMEOUT < timezone.now():
        # Timeout, cancel job
        cancel_current_task()
    if payment_order.outgoing_tx_id is not None:
        # Payment already forwarded, cancel job
        cancel_current_task()
        return
    if payment_order.incoming_tx_id is not None:
        try:
            incoming_tx_reliable = blockcypher.is_tx_reliable(
                payment_order.incoming_tx_id,
                payment_order.bitcoin_network)
        except Exception as error:
            # Error when accessing blockcypher API
            logger.exception(error)
            cancel_current_task()
            return
        if not incoming_tx_reliable:
            # Wait
            return
        cancel_current_task()
        forward_transaction(payment_order)
        run_periodic_task(wait_for_confirmation, [payment_order.uid], interval=15)
        if payment_order.instantfiat_invoice_id is None:
            # Payment finished
            logger.info('payment order closed ({0})'.format(payment_order.uid))
        else:
            run_periodic_task(wait_for_exchange, [payment_order.uid])


def forward_transaction(payment_order):
    """
    Accepts:
        payment_order: PaymentOrder instance
    """
    # Connect to bitcoind
    bc = blockchain.BlockChain(payment_order.device.bitcoin_network)
    # Wait for transaction
    incoming_tx = bc.get_raw_transaction(payment_order.incoming_tx_id)
    # Get outputs
    unspent_outputs = bc.get_unspent_outputs(
        CBitcoinAddress(payment_order.local_address))
    total_available = sum(out['amount'] for out in unspent_outputs)
    payment_order.extra_btc_amount = total_available - payment_order.btc_amount
    # Select destination address
    btc_account = BTCAccount.objects.filter(
        merchant=payment_order.device.merchant,
        network=payment_order.device.bitcoin_network).first()
    if btc_account and \
            btc_account.balance + payment_order.merchant_btc_amount <= \
            btc_account.balance_max:
        # Store bitcoins on merchant's internal account
        if not btc_account.address:
            btc_account.address = str(bc.get_new_address())
        destination_address = btc_account.address
        btc_account.balance += payment_order.merchant_btc_amount
    else:
        # Forward payment to merchant address (default)
        destination_address = payment_order.merchant_address
    # Forward payment
    addresses = [
        (destination_address,
         payment_order.merchant_btc_amount),
        (payment_order.fee_address,
         payment_order.fee_btc_amount + payment_order.extra_btc_amount),
        (payment_order.instantfiat_address,
         payment_order.instantfiat_btc_amount),
    ]
    outputs = {}
    for address, amount in addresses:
        if not address:
            continue
        if address not in outputs:
            outputs[address] = BTC_DEC_PLACES
        outputs[address] += amount
    outgoing_tx = bc.create_raw_transaction(
        [out['outpoint'] for out in unspent_outputs],
        outputs)
    outgoing_tx_signed = bc.sign_raw_transaction(outgoing_tx)
    payment_order.outgoing_tx_id = bc.send_raw_transaction(outgoing_tx_signed)
    payment_order.time_forwarded = timezone.now()
    payment_order.save()
    if btc_account:
        btc_account.save()


def wait_for_confirmation(order_uid):
    """
    Asynchronous task
    Accepts:
        order_uid: PaymentOrder unique identifier
    """
    try:
        order = PaymentOrder.objects.get(uid=order_uid)
    except PaymentOrder.DoesNotExist:
        # PaymentOrder deleted, cancel job
        cancel_current_task()
        return
    if order.time_created + PAYMENT_CONFIRMATION_TIMEOUT < timezone.now():
        # Timeout, cancel job
        cancel_current_task()
    bc = blockchain.BlockChain(order.bitcoin_network)
    if bc.is_tx_confirmed(order.outgoing_tx_id):
        cancel_current_task()
        if order.time_confirmed is None:
            order.time_confirmed = timezone.now()
            order.save()


def wait_for_exchange(payment_order_uid):
    """
    Asynchronous task
    Accepts:
        payment_order_uid: PaymentOrder unique identifier
    """
    try:
        payment_order = PaymentOrder.objects.get(uid=payment_order_uid)
    except PaymentOrder.DoesNotExist:
        # PaymentOrder deleted, cancel job
        cancel_current_task()
        return
    if payment_order.time_created + PAYMENT_EXCHANGE_TIMEOUT < timezone.now():
        # Timeout, cancel job
        cancel_current_task()
    invoice_paid = instantfiat.is_invoice_paid(
        payment_order.device.merchant,
        payment_order.instantfiat_invoice_id)
    if invoice_paid:
        cancel_current_task()
        if payment_order.time_exchanged is not None:
            # Already exchanged, skip
            return
        payment_order.time_exchanged = timezone.now()
        payment_order.save()
        logger.info('payment order closed ({0})'.format(payment_order.uid))


def check_payment_status(payment_order_uid):
    """
    Asynchronous task
    """
    try:
        payment_order = PaymentOrder.objects.get(uid=payment_order_uid)
    except PaymentOrder.DoesNotExist:
        # PaymentOrder deleted, cancel job
        cancel_current_task()
        return
    if payment_order.status in ['failed', 'refunded']:
        cancel_current_task()
        send_error_message(payment_order=payment_order)
    elif payment_order.status in ['timeout', 'confirmed']:
        cancel_current_task()

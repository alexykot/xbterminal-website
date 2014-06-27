"""
Payment
"""
import datetime
from decimal import Decimal
import time

from bitcoin.wallet import CBitcoinAddress
import rq

from django.utils import timezone
import constance.config
import django_rq

import payment.average
import payment.blockchain
import payment.instantfiat

from website.models import PaymentOrder, Transaction

FIAT_DEC_PLACES = Decimal('0.00000000')
BTC_DEC_PLACES  = Decimal('0.00000000')
BTC_DEFAULT_FEE = Decimal('0.00010000')
BTC_MIN_OUTPUT  = Decimal('0.00005460')


def create_invoice(amount_instantfiat_fiat, currency, instantfiat_service):
    instantfiat_mod = getattr(payment.instantfiat, instantfiat_service)
    invoice_data = instantfiat_mod.create_invoice(
        amount_instantfiat, currency)
    return invoice_data


def prepare_payment(device, fiat_amount):
    """
    Accepts:
        device: website.models.Device
        amount_fiat: Decimal
    Returns:
        payment_order: PaymentOrder instance
    """
    details = {
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
        'btc_amount': BTC_DEC_PLACES,
        'effective_exchange_rate': None,
        'instantfiat_invoice_id': None,
    }
    # Connect to bitcoind
    bc = payment.blockchain.BlockChain(device.bitcoin_network)
    # Addresses
    details['local_address'] = str(bc.get_new_address())
    details['merchant_address'] = device.bitcoin_address
    if device.our_fee_override:
        details['fee_address'] = device.our_fee_override
    else:
        details['fee_address'] = constance.config.OUR_FEE_BITCOIN_ADDRESS
    # Exchange service
    details['fiat_currency'] = device.currency.name
    details['fiat_amount'] = fiat_amount.quantize(FIAT_DEC_PLACES)
    instantfiat_service = device.payment_processor
    instantfiat_share = Decimal(device.percent / 100 if device.percent else 0)
    if instantfiat_service is not None and instantfiat_share > 0:
        details['instantfiat_fiat_amount'] = (details['fiat_amount'] *
                                              instantfiat_share).quantize(FIAT_DEC_PLACES)
        invoice_data = create_invoice(details['instantfiat_fiat_amount'],
                                      details['fiat_currency'],
                                      instantfiat_service)
        details['instantfiat_invoice_id'] = invoice_data['invoice_id']
        details['instantfiat_address'] = invoice_data['address']
        details['instantfiat_btc_amount'] = invoice_data['amount_btc']
        exchange_rate = details['instantfiat_fiat_amount'] / details['instantfiat_btc_amount']
    else:
        exchange_rate = payment.average.get_exchange_rate(details['fiat_currency'])
    # Fee
    details['fee_btc_amount'] = (details['fiat_amount'] *
                                 Decimal(constance.config.OUR_FEE_SHARE) /
                                 exchange_rate).quantize(BTC_DEC_PLACES)
    if details['fee_btc_amount'] < BTC_MIN_OUTPUT:
        details['fee_btc_amount'] = BTC_DEC_PLACES
    # Merchant
    details['merchant_btc_amount'] = ((details['fiat_amount'] - details['instantfiat_fiat_amount']) /
                                      exchange_rate).quantize(BTC_DEC_PLACES)
    if 0 < details['merchant_btc_amount'] < BTC_MIN_OUTPUT:
        details['merchant_btc_amount'] = BTC_MIN_OUTPUT
    # Total
    details['btc_amount'] = (details['merchant_btc_amount'] +
                             details['instantfiat_btc_amount'] +
                             details['fee_btc_amount'] +
                             BTC_DEFAULT_FEE)
    details['effective_exchange_rate'] = details['fiat_amount'] / details['btc_amount']
    # Prepare payment order
    now = timezone.localtime(timezone.now())
    payment_order = PaymentOrder(
        device=device,
        created=now,
        expires=now + datetime.timedelta(minutes=10),
        **details)
    # Schedule tasks
    scheduler = django_rq.get_scheduler()
    scheduler.schedule(
        scheduled_time=timezone.now(),
        func=wait_for_payment,
        args=[payment_order.uid],
        interval=2,
        repeat=450,  # Repeat for 15 minutes
        result_ttl=3600)
    scheduler.schedule(
        scheduled_time=timezone.now(),
        func=wait_for_validation,
        args=[payment_order.uid],
        interval=2,
        repeat=600,  # Repeat for 20 minutes
        result_ttl=3600)
    return payment_order


def wait_for_payment(payment_order_uid):
    """
    Asynchronous task
    Accepts:
        payment_order_uid: PaymentOrder unique identifier
    """
    # Check current balance
    payment_order = PaymentOrder.objects.get(uid=payment_order_uid)
    if payment_order.incoming_tx_id is not None:
        # Payment already validated, cancel task
        django_rq.get_scheduler().cancel(rq.get_current_job())
        return
    # Connect to bitcoind
    bc = payment.blockchain.BlockChain(payment_order.device.bitcoin_network)
    transactions = bc.get_unspent_transactions(
        CBitcoinAddress(payment_order.local_address))
    if transactions:
        validate_payment(payment_order, transactions)
        django_rq.get_scheduler().cancel(rq.get_current_job())


class InvalidPayment(Exception):

    def __init__(self, error_message):
        super(InvalidPayment, self).__init__()
        self.error_message = error_message

    def __str__(self):
        return "Invalid payment: {0}".format(self.error_message)


def validate_payment(payment_order, transactions):
    """
    Validates payment and stores incoming transaction id
    in PaymentOrder instance
    Accepts:
        payment_order: PaymentOrder instance
        transactions: list of CTransaction
    """
    bc = payment.blockchain.BlockChain(payment_order.device.bitcoin_network)
    if len(transactions) != 1:
        raise InvalidPayment('expecting single transaction')
    incoming_tx = transactions[0]
    # Validate transaction
    if not bc.is_valid_transaction(incoming_tx):
        raise InvalidPayment('invalid transaction')
    # Check amount
    btc_amount = BTC_DEC_PLACES
    for output in payment.blockchain.get_tx_outputs(incoming_tx):
        if str(output['address']) == payment_order.local_address:
            btc_amount += output['amount']
    if btc_amount < payment_order.btc_amount:
        raise InvalidPayment('insufficient funds')
    # Save incoming transaction id
    payment_order.incoming_tx_id = payment.blockchain.get_txid(incoming_tx)
    payment_order.save()


def wait_for_validation(payment_order_uid):
    """
    Asynchronous task
    Accepts:
        payment_order_uid: PaymentOrder unique identifier
    """
    payment_order = PaymentOrder.objects.get(uid=payment_order_uid)
    if payment_order.incoming_tx_id is not None:
        django_rq.get_scheduler().cancel(rq.get_current_job())
        if payment_order.transaction is not None:
            # Payment already forwarded, skip
            return
        forward_transaction(payment_order)


def forward_transaction(payment_order):
    """
    Accepts:
        payment_order: PaymentOrder instance
    """
    # Connect to bitcoind
    bc = payment.blockchain.BlockChain(payment_order.device.bitcoin_network)
    # Wait for transaction
    incoming_tx = None
    while incoming_tx is None:
        try:
            incoming_tx = bc.get_raw_transaction(payment_order.incoming_tx_id)
        except IndexError as error:
            pass
        time.sleep(1)
    unspent_outputs = bc.get_unspent_outputs(
        CBitcoinAddress(payment_order.local_address))
    total_available = sum(out['amount'] for out in unspent_outputs)
    excess_amount = max(total_available - payment_order.btc_amount,
                        BTC_DEC_PLACES)
    # Forward payment
    outputs = {
        payment_order.merchant_address: payment_order.merchant_btc_amount,
        payment_order.fee_address: payment_order.fee_btc_amount + excess_amount,
        payment_order.instantfiat_address: payment_order.instantfiat_btc_amount,
    }
    outgoing_tx = bc.create_raw_transaction(
        [out['outpoint'] for out in unspent_outputs],
        outputs)
    outgoing_tx_signed = bc.sign_raw_transaction(outgoing_tx)
    outgoing_tx_id = bc.send_raw_transaction(outgoing_tx_signed)
    # Save transaction info
    transaction = Transaction(
        device=payment_order.device,
        hop_address=payment_order.local_address,
        dest_address=payment_order.merchant_address,
        instantfiat_address=payment_order.instantfiat_address,
        bitcoin_transaction_id_1=payment_order.incoming_tx_id,
        bitcoin_transaction_id_2=outgoing_tx_id,
        fiat_currency=payment_order.fiat_currency,
        fiat_amount=payment_order.fiat_amount,
        btc_amount=payment_order.btc_amount + excess_amount,
        effective_exchange_rate=payment_order.effective_exchange_rate,
        instantfiat_fiat_amount=payment_order.instantfiat_fiat_amount,
        instantfiat_btc_amount=payment_order.instantfiat_btc_amount,
        fee_btc_amount=payment_order.fee_btc_amount + excess_amount,
        instantfiat_invoice_id=payment_order.instantfiat_invoice_id,
        time=timezone.now())
    transaction.save()
    payment_order.transaction = transaction
    payment_order.save()
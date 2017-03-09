"""
Payment operations
"""
from decimal import Decimal
import logging

from bitcoin.rpc import JSONRPCError
from bitcoin.wallet import CBitcoinAddress

from django.utils import timezone
from django.db.transaction import atomic
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
from operations.services.wrappers import get_exchange_rate, is_tx_reliable
from operations.models import PaymentOrder

from website.models import Device, Account
from website.utils.accounts import create_account_txs
from api.utils.urls import get_admin_url
from common.rq_helpers import run_periodic_task, cancel_current_task

logger = logging.getLogger(__name__)


def prepare_payment(device_or_account, fiat_amount):
    """
    Accepts:
        device_or_account: Device or Account instance
        fiat_amount: Decimal
    Returns:
        order: PaymentOrder instance
    """
    if isinstance(device_or_account, Device):
        device = device_or_account
        account = device.account
    elif isinstance(device_or_account, Account):
        device = None
        account = device_or_account
    assert fiat_amount >= FIAT_MIN_OUTPUT
    if not account:
        raise exceptions.PaymentError(
            'Account is not set for device.')
    if not account.instantfiat and not account.forward_address:
        raise exceptions.PaymentError(
            'Payout address is not set for account.')
    if account.instantfiat and \
            account.merchant.currency != account.currency:
        raise exceptions.PaymentError(
            'Account currency should match merchant currency.')
    # Prepare payment order
    # TODO: fiat currency -> currency
    order = PaymentOrder(
        device=device,
        account=account,
        bitcoin_network=account.bitcoin_network,
        merchant_address=account.forward_address,
        fiat_currency=account.merchant.currency,
        fiat_amount=fiat_amount.quantize(FIAT_DEC_PLACES))
    # Connect to bitcoind
    bc = blockchain.BlockChain(order.bitcoin_network)
    # Local address (payment address)
    try:
        order.local_address = str(bc.get_new_address())
    except Exception as error:
        logger.exception(error)
        raise exceptions.NetworkError
    # Fee address
    if device and device.our_fee_override:
        order.fee_address = device.our_fee_override
    elif order.bitcoin_network == 'mainnet':
        order.fee_address = config.OUR_FEE_MAINNET_ADDRESS
    elif order.bitcoin_network == 'testnet':
        order.fee_address = config.OUR_FEE_TESTNET_ADDRESS
    # Exchange service
    if not account.instantfiat:
        order.instantfiat_fiat_amount = FIAT_DEC_PLACES
        order.instantfiat_btc_amount = BTC_DEC_PLACES
        exchange_rate = get_exchange_rate(order.fiat_currency.name)
    else:
        order.instantfiat_fiat_amount = order.fiat_amount
        (order.instantfiat_invoice_id,
         order.instantfiat_btc_amount,
         order.instantfiat_address) = instantfiat.create_invoice(
            account,
            order.instantfiat_fiat_amount)
        assert order.instantfiat_btc_amount > 0
        if order.instantfiat_btc_amount < BTC_MIN_OUTPUT:
            order.instantfiat_btc_amount = BTC_MIN_OUTPUT
        exchange_rate = order.instantfiat_fiat_amount / order.instantfiat_btc_amount
    # Validate addresses
    for address_field in ['local_address', 'merchant_address',
                          'fee_address', 'instantfiat_address']:
        address = getattr(order, address_field)
        if address:
            error_message = blockchain.validate_bitcoin_address(
                address, order.bitcoin_network)
            assert error_message is None
    # Fee
    order.fee_btc_amount = (order.fiat_amount *
                            Decimal(config.OUR_FEE_SHARE) /
                            exchange_rate).quantize(BTC_DEC_PLACES)
    if order.fee_btc_amount < BTC_MIN_OUTPUT:
        logger.warning(
            'Payment fee is zero',
            extra={'data': {'order_uid': order.uid}})
        order.fee_btc_amount = BTC_DEC_PLACES
    # Merchant
    order.merchant_btc_amount = ((order.fiat_amount - order.instantfiat_fiat_amount) /
                                 exchange_rate).quantize(BTC_DEC_PLACES)
    assert order.merchant_btc_amount >= 0
    if 0 < order.merchant_btc_amount < BTC_MIN_OUTPUT:
        order.merchant_btc_amount = BTC_MIN_OUTPUT
    # TX fee
    if not account.instantfiat and \
            account.balance + order.merchant_btc_amount <= account.balance_max:
        # Output will be splitted, adjust fee
        n_outputs = 2 + len(blockchain.split_amount(
            order.merchant_btc_amount,
            config.POOL_TX_MAX_OUTPUT))
    else:
        n_outputs = 3
    order.tx_fee_btc_amount = bc.get_tx_fee(1, n_outputs)
    # Save order
    order.save()
    # Schedule tasks
    run_periodic_task(wait_for_payment, [order.uid], interval=2)
    run_periodic_task(wait_for_validation, [order.uid], interval=5)
    run_periodic_task(check_payment_status, [order.uid], interval=60)
    return order


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
    if payment_order.time_received is not None:
        # Payment already validated, cancel job
        cancel_current_task()
        return
    if payment_order.status == 'cancelled':
        cancel_current_task()
        return
    # Connect to bitcoind
    bc = blockchain.BlockChain(payment_order.bitcoin_network)
    transactions = bc.get_unspent_transactions(
        CBitcoinAddress(payment_order.local_address))
    if transactions:
        if len(transactions) > 1:
            logger.warning('multiple incoming tx')
        # Save tx ids
        for incoming_tx in transactions:
            incoming_tx_id = blockchain.get_txid(incoming_tx)
            if incoming_tx_id not in payment_order.incoming_tx_ids:
                payment_order.incoming_tx_ids.append(incoming_tx_id)
        # Save refund address
        tx_inputs = bc.get_tx_inputs(transactions[0])
        if len(tx_inputs) > 1:
            logger.warning('incoming tx contains more than one input')
        payment_order.refund_address = str(tx_inputs[0]['address'])
        payment_order.save()
        # Validate payment
        try:
            validate_payment(payment_order, transactions)
        except exceptions.InsufficientFunds:
            # Don't cancel task, wait for next transaction
            pass
        except Exception as error:
            cancel_current_task()
            logger.exception(error)
        else:
            cancel_current_task()
            # Update status
            payment_order.payment_type = 'bip0021'
            payment_order.time_received = timezone.now()
            payment_order.save()
            logger.info('payment received ({0})'.format(payment_order.uid))


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
    bc = blockchain.BlockChain(payment_order.bitcoin_network)
    try:
        (transactions,
         refund_addresses,
         payment_ack) = protocol.parse_payment(payment_message)
    except Exception as error:
        raise exceptions.InvalidPaymentMessage
    # Broadcast transactions, save ids
    for incoming_tx in transactions:
        try:
            incoming_tx_signed = bc.sign_raw_transaction(incoming_tx)
            bc.send_raw_transaction(incoming_tx_signed)
        except JSONRPCError as error:
            logger.exception(error)
        incoming_tx_id = blockchain.get_txid(incoming_tx)
        if incoming_tx_id not in payment_order.incoming_tx_ids:
            payment_order.incoming_tx_ids.append(incoming_tx_id)
    # Save refund address
    if refund_addresses:
        payment_order.refund_address = refund_addresses[0]
    payment_order.save()
    # Validate payment
    validate_payment(payment_order, transactions)
    # Update status
    payment_order.payment_type = 'bip0070'
    payment_order.time_received = timezone.now()
    payment_order.save()
    logger.info('payment received ({0})'.format(payment_order.uid))
    return payment_ack


def validate_payment(payment_order, transactions):
    """
    Validates payment
    Accepts:
        payment_order: PaymentOrder instance
        transactions: list of CTransaction
    """
    bc = blockchain.BlockChain(payment_order.bitcoin_network)
    # Validate transactions
    for incoming_tx in transactions:
        bc.sign_raw_transaction(incoming_tx)
    # Check amount
    btc_amount = BTC_DEC_PLACES
    for incoming_tx in transactions:
        for output in bc.get_tx_outputs(incoming_tx):
            if str(output['address']) == payment_order.local_address:
                btc_amount += output['amount']
    payment_order.paid_btc_amount = btc_amount
    payment_order.save()
    if payment_order.status == 'underpaid':
        raise exceptions.InsufficientFunds


def reverse_payment(order):
    """
    Send all money back to customer
    Accepts:
        order: PaymentOrder instance
    """
    if order.time_forwarded is not None:
        raise exceptions.RefundError
    if order.time_refunded is not None:
        raise exceptions.RefundError
    if not order.refund_address:
        raise exceptions.RefundError
    bc = blockchain.BlockChain(order.bitcoin_network)
    tx_inputs = []
    amount = BTC_DEC_PLACES
    for output in bc.get_unspent_outputs(order.local_address):
        tx_inputs.append(output['outpoint'])
        amount += output['amount']
    if not amount:
        raise exceptions.RefundError
    amount -= bc.get_tx_fee(1, 1)
    tx_outputs = {order.refund_address: amount}
    refund_tx = bc.create_raw_transaction(tx_inputs, tx_outputs)
    refund_tx_signed = bc.sign_raw_transaction(refund_tx)
    refund_tx_id = bc.send_raw_transaction(refund_tx_signed)
    # Changing order status, customer should be notified
    order.refund_tx_id = refund_tx_id
    order.time_refunded = timezone.now()
    order.save()
    logger.warning(
        'Payment returned',
        extra={'data': {
            'order_uid': order.uid,
            'order_admin_url': get_admin_url(order),
        }})


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
    if payment_order.time_forwarded is not None:
        # Payment already forwarded, cancel job
        cancel_current_task()
        return
    if payment_order.status == 'cancelled':
        cancel_current_task()
        return
    if payment_order.time_received is not None:
        for incoming_tx_id in payment_order.incoming_tx_ids:
            if not is_tx_reliable(incoming_tx_id,
                                  payment_order.bitcoin_network):
                # Break cycle, wait for confidence
                break
        else:
            cancel_current_task()
            with atomic():
                payment_order.refresh_from_db()
                if payment_order.status == 'cancelled':
                    # Payment still can be cancelled at this moment
                    return
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
    bc = blockchain.BlockChain(payment_order.bitcoin_network)
    # Get outputs
    unspent_outputs = bc.get_unspent_outputs(
        CBitcoinAddress(payment_order.local_address))
    payment_order.paid_btc_amount = sum(out['amount'] for out in unspent_outputs)
    # Extra
    extra_btc_amount = payment_order.paid_btc_amount - payment_order.btc_amount
    if extra_btc_amount > BTC_MIN_OUTPUT:
        payment_order.extra_btc_amount = extra_btc_amount
    else:
        payment_order.tx_fee_btc_amount += extra_btc_amount
    # Select output addresses
    outputs = [
        (payment_order.fee_address,
         payment_order.fee_btc_amount),
        (payment_order.refund_address,
         payment_order.extra_btc_amount),
    ]
    account = payment_order.account
    if account.instantfiat:
        assert not payment_order.merchant_btc_amount
        outputs.append((payment_order.instantfiat_address,
                        payment_order.instantfiat_btc_amount))
        create_account_txs(payment_order)
    else:
        assert not payment_order.instantfiat_btc_amount
        if account.balance + payment_order.merchant_btc_amount <= \
                account.balance_max:
            # Store bitcoins on merchant's internal account
            splitted = blockchain.split_amount(
                payment_order.merchant_btc_amount,
                config.POOL_TX_MAX_OUTPUT)
            account_addrs = list(account.address_set.order_by('created_at'))
            for idx, amount in enumerate(splitted):
                try:
                    address = account_addrs[idx].address
                except IndexError:
                    address = str(bc.get_new_address())
                    account.address_set.create(address=address)
                outputs.append((address, amount))
            create_account_txs(payment_order)
        else:
            # Forward payment to merchant address
            outputs.append((payment_order.merchant_address,
                            payment_order.merchant_btc_amount))
    # Create and send transaction
    summed_outputs = {}
    for address, amount in outputs:
        assert address
        if address not in summed_outputs:
            summed_outputs[address] = BTC_DEC_PLACES
        summed_outputs[address] += amount
    outgoing_tx = bc.create_raw_transaction(
        [out['outpoint'] for out in unspent_outputs],
        summed_outputs)
    outgoing_tx_signed = bc.sign_raw_transaction(outgoing_tx)
    payment_order.outgoing_tx_id = bc.send_raw_transaction(outgoing_tx_signed)
    payment_order.time_forwarded = timezone.now()
    payment_order.save()


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


def check_confirmation(order):
    """
    Check outgoing transaction for confirmation
    Accepts:
        order: PaymentOrder or WithdrawalOrder instance
    """
    if order.time_confirmed is not None:
        return True
    bc = blockchain.BlockChain(order.bitcoin_network)
    if bc.is_tx_confirmed(order.outgoing_tx_id):
        order.time_confirmed = timezone.now()
        order.save()
        return True
    else:
        return False


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
        payment_order.account,
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
    if payment_order.status in ['timeout', 'cancelled']:
        try:
            reverse_payment(payment_order)
        except exceptions.RefundError:
            pass
        cancel_current_task()
    elif payment_order.status == 'failed':
        try:
            reverse_payment(payment_order)
        except exceptions.RefundError:
            pass
        logger.error(
            'Payment failed',
            extra={'data': {
                'order_uid': payment_order.uid,
                'order_admin_url': get_admin_url(payment_order),
            }})
        cancel_current_task()
    elif payment_order.status == 'unconfirmed':
        logger.error(
            'Payment error - outgoing transaction not confirmed',
            extra={'data': {
                'order_uid': payment_order.uid,
                'order_admin_url': get_admin_url(payment_order),
            }})
        cancel_current_task()
    elif payment_order.status in ['refunded', 'confirmed']:
        cancel_current_task()

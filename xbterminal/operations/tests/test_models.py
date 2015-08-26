import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from operations.models import WithdrawalOrder
from operations.tests.factories import (
    DeviceFactory,
    PaymentOrderFactory,
    WithdrawalOrderFactory)


class PaymentOrderTestCase(TestCase):

    def test_payment_order_factory(self):
        payment_order = PaymentOrderFactory.create()
        self.assertEqual(payment_order.order_type, 'payment')
        self.assertEqual(len(payment_order.uid), 6)
        self.assertEqual(payment_order.status, 'new')
        self.assertEqual(payment_order.bitcoin_network,
                         payment_order.device.bitcoin_network)

        expected_btc_amount = (payment_order.merchant_btc_amount +
                               payment_order.instantfiat_btc_amount +
                               payment_order.fee_btc_amount +
                               payment_order.tx_fee_btc_amount)
        self.assertEqual(payment_order.btc_amount, expected_btc_amount)

    def test_status(self):
        # Without instantfiat
        payment_order = PaymentOrderFactory.create()
        self.assertEqual(payment_order.status, 'new')
        payment_order.time_recieved = (payment_order.time_created +
                                       datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'recieved')
        self.assertFalse(payment_order.is_receipt_ready())
        payment_order.time_forwarded = (payment_order.time_recieved +
                                        datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'processed')
        self.assertTrue(payment_order.is_receipt_ready())
        payment_order.time_finished = (payment_order.time_forwarded +
                                       datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'completed')
        # With instantfiat
        payment_order = PaymentOrderFactory.create(
            instantfiat_invoice_id='invoice01')
        self.assertEqual(payment_order.status, 'new')
        payment_order.time_recieved = (payment_order.time_created +
                                       datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'recieved')
        self.assertFalse(payment_order.is_receipt_ready())
        payment_order.time_forwarded = (payment_order.time_recieved +
                                        datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'forwarded')
        self.assertTrue(payment_order.is_receipt_ready())
        payment_order.time_exchanged = (payment_order.time_forwarded +
                                        datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'processed')
        payment_order.time_finished = (payment_order.time_exchanged +
                                       datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'completed')
        # Timeout
        payment_order = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(payment_order.status, 'timeout')
        # Failed
        payment_order = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=2),
            time_recieved=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(payment_order.status, 'failed')

    def test_scaled_btc_amount(self):
        order = PaymentOrderFactory.create(btc_amount=Decimal('0.1003'))
        self.assertEqual(order.scaled_btc_amount, Decimal('100.3'))

    def test_scaled_effective_exchange_rate(self):
        order = PaymentOrderFactory.create(
            effective_exchange_rate=Decimal('220'))
        self.assertEqual(order.scaled_effective_exchange_rate,
                         Decimal('0.22'))

    def test_urls_for_receipts(self):
        order = PaymentOrderFactory.create(incoming_tx_id='0' * 64)
        self.assertIsNotNone(order.payment_address_url)
        self.assertIsNotNone(order.incoming_tx_url)


class WithdrawalOrderTestCase(TestCase):

    def test_create_order(self):
        device = DeviceFactory.create()
        order = WithdrawalOrder.objects.create(
            device=device,
            bitcoin_network=device.bitcoin_network,
            merchant_address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE',
            fiat_currency=device.merchant.currency,
            fiat_amount=Decimal('0.5'),
            customer_btc_amount=Decimal('0.05'),
            tx_fee_btc_amount=Decimal('0.0001'),
            change_btc_amount=Decimal(0),
            exchange_rate=Decimal('10'))
        # Defaults
        self.assertEqual(order.order_type, 'withdrawal')
        self.assertEqual(len(order.uid), 6)
        self.assertIsNotNone(order.time_created)
        self.assertEqual(str(order), order.uid)

    def test_factory(self):
        order = WithdrawalOrderFactory.create()
        self.assertEqual(order.bitcoin_network,
                         order.device.bitcoin_network)
        self.assertEqual(order.fiat_currency,
                         order.device.merchant.currency)

    def test_btc_amount(self):
        order = WithdrawalOrderFactory.create(
            customer_btc_amount=Decimal('0.1'),
            tx_fee_btc_amount=Decimal('0.0002'),
            change_btc_amount=Decimal('0.2'))
        self.assertEqual(order.btc_amount, Decimal('0.1002'))
        self.assertEqual(order.scaled_btc_amount, Decimal('100.2'))

    def test_effective_exchange_rate(self):
        order = WithdrawalOrderFactory.create(
            fiat_amount=Decimal('1.00'),
            customer_btc_amount=Decimal('0.05'),
            tx_fee_btc_amount=Decimal('0.05'))
        self.assertEqual(order.effective_exchange_rate, Decimal('10'))
        self.assertEqual(order.scaled_effective_exchange_rate,
                         Decimal('0.01'))

    def test_status(self):
        order = WithdrawalOrderFactory.create()
        self.assertEqual(order.status, 'new')
        order.time_sent = timezone.now()
        self.assertEqual(order.status, 'sent')
        order.time_broadcasted = timezone.now()
        self.assertEqual(order.status, 'broadcasted')
        order.time_completed = timezone.now()
        self.assertEqual(order.status, 'completed')

        order = WithdrawalOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(order.status, 'timeout')

        order = WithdrawalOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=2),
            time_sent=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(order.status, 'failed')

    def test_urls_for_receipts(self):
        order = WithdrawalOrderFactory.create(outgoing_tx_id='0' * 64)
        self.assertIsNotNone(order.customer_address_url)
        self.assertIsNotNone(order.outgoing_tx_url)

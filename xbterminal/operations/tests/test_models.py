import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from operations.models import WithdrawalOrder
from operations.tests.factories import (
    DeviceFactory,
    PaymentOrderFactory,
    WithdrawalOrderFactory)
from website.tests.factories import AccountFactory


class PaymentOrderTestCase(TestCase):

    def test_factory(self):
        payment_order = PaymentOrderFactory.create()
        self.assertEqual(payment_order.order_type, 'payment')
        self.assertEqual(len(payment_order.uid), 6)
        self.assertEqual(payment_order.status, 'new')
        self.assertEqual(payment_order.account.pk,
                         payment_order.device.account.pk)
        self.assertEqual(payment_order.bitcoin_network,
                         payment_order.account.bitcoin_network)
        self.assertEqual(payment_order.fiat_currency.pk,
                         payment_order.account.merchant.currency.pk)
        self.assertEqual(len(payment_order.incoming_tx_ids), 0)

        expected_btc_amount = (payment_order.merchant_btc_amount +
                               payment_order.instantfiat_btc_amount +
                               payment_order.fee_btc_amount +
                               payment_order.tx_fee_btc_amount)
        self.assertEqual(payment_order.btc_amount, expected_btc_amount)
        self.assertEqual(payment_order.paid_btc_amount, 0)
        self.assertEqual(payment_order.extra_btc_amount, 0)

    def test_incoming_tx_ids(self):
        order = PaymentOrderFactory.create()
        tx_1 = '1' * 64
        tx_2 = '2' * 64
        order.incoming_tx_ids.append(tx_1)
        order.incoming_tx_ids.append(tx_2)
        self.assertIn(tx_1, order.incoming_tx_ids)
        self.assertIn(tx_2, order.incoming_tx_ids)
        order.save()
        self.assertEqual(len(order.incoming_tx_ids), 2)

    def test_merchant(self):
        order = PaymentOrderFactory.create()
        self.assertEqual(order.merchant.pk, order.device.merchant.pk)
        account = AccountFactory.create()
        order = PaymentOrderFactory.create(device=None, account=account)
        self.assertEqual(order.merchant.pk, account.merchant.pk)

    def test_status(self):
        # Without instantfiat
        payment_order = PaymentOrderFactory.create()
        self.assertEqual(payment_order.status, 'new')
        payment_order.incoming_tx_ids.append('0' * 64)
        self.assertEqual(payment_order.status, 'underpaid')
        payment_order.time_recieved = (payment_order.time_created +
                                       datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'recieved')
        payment_order.time_forwarded = (payment_order.time_recieved +
                                        datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'processed')
        payment_order.time_notified = (payment_order.time_forwarded +
                                       datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'notified')
        payment_order.time_confirmed = (payment_order.time_notified +
                                        datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'confirmed')
        # With instantfiat
        payment_order = PaymentOrderFactory.create(
            instantfiat_invoice_id='invoice01')
        self.assertEqual(payment_order.status, 'new')
        payment_order.time_recieved = (payment_order.time_created +
                                       datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'recieved')
        payment_order.time_forwarded = (payment_order.time_recieved +
                                        datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'forwarded')
        payment_order.time_exchanged = (payment_order.time_forwarded +
                                        datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'processed')
        payment_order.time_notified = (payment_order.time_exchanged +
                                       datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'notified')
        payment_order.time_confirmed = (payment_order.time_notified +
                                        datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'confirmed')
        # Timeout
        payment_order = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(payment_order.status, 'timeout')
        # Failed
        payment_order = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=2),
            time_recieved=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(payment_order.status, 'failed')
        # Unconfirmed
        payment_order = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=5),
            time_recieved=timezone.now() - datetime.timedelta(hours=5),
            time_forwarded=timezone.now() - datetime.timedelta(hours=5),
            time_notified=timezone.now() - datetime.timedelta(hours=5))
        self.assertEqual(payment_order.status, 'unconfirmed')
        # Refunded
        payment_order = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=2),
            time_recieved=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(payment_order.status, 'failed')
        payment_order.time_refunded = (payment_order.time_recieved +
                                       datetime.timedelta(minutes=10))
        self.assertEqual(payment_order.status, 'refunded')
        # Cancelled
        order = PaymentOrderFactory.create()
        self.assertEqual(order.status, 'new')
        order.time_cancelled = timezone.now()
        self.assertEqual(order.status, 'cancelled')

    def test_btc_amount(self):
        order = PaymentOrderFactory.create(
            merchant_btc_amount=Decimal('0.1'),
            instantfiat_btc_amount=Decimal('0.1'),
            fee_btc_amount=Decimal('0.01'),
            tx_fee_btc_amount=Decimal('0.0002'))
        self.assertEqual(order.btc_amount, Decimal('0.2102'))
        self.assertEqual(order.scaled_btc_amount, Decimal('210.2'))

    def test_effective_exchange_rate(self):
        order = PaymentOrderFactory.create(
            fiat_amount=Decimal('1.00'),
            merchant_btc_amount=Decimal('0.05'),
            tx_fee_btc_amount=Decimal('0.05'))
        self.assertEqual(order.effective_exchange_rate, Decimal('10'))
        self.assertEqual(order.scaled_effective_exchange_rate,
                         Decimal('0.01'))

    def test_urls_for_receipts(self):
        order = PaymentOrderFactory.create(incoming_tx_ids=['0' * 64])
        self.assertIn('/prc/{0}'.format(order.uid), order.receipt_url)

    def test_create_payment_request(self):
        order = PaymentOrderFactory.create()
        url = 'http://some-url'
        request = order.create_payment_request(url)
        self.assertTrue(isinstance(request, bytes))
        self.assertGreater(len(request), 0)


class WithdrawalOrderTestCase(TestCase):

    def test_create_order(self):
        device = DeviceFactory.create()
        order = WithdrawalOrder.objects.create(
            device=device,
            account=device.account,
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
        self.assertIsNone(order.instantfiat_transfer_id)
        self.assertIsNone(order.instantfiat_reference)
        self.assertIsNotNone(order.time_created)
        self.assertEqual(str(order), order.uid)

    def test_factory(self):
        order = WithdrawalOrderFactory.create()
        self.assertEqual(order.account.pk,
                         order.device.account.pk)
        self.assertEqual(order.bitcoin_network,
                         order.device.bitcoin_network)
        self.assertEqual(order.fiat_currency,
                         order.account.merchant.currency)
        self.assertIsNotNone(order.merchant_address)

    def test_factory_instantfiat(self):
        order = WithdrawalOrderFactory.create(
            device__account__currency__name='GBP')
        self.assertEqual(order.fiat_currency,
                         order.account.merchant.currency)
        self.assertIsNone(order.merchant_address)

    def test_merchant(self):
        order = WithdrawalOrderFactory.create()
        self.assertEqual(order.merchant.pk, order.device.merchant.pk)
        account = AccountFactory.create()
        order = WithdrawalOrderFactory.create(device=None, account=account)
        self.assertEqual(order.merchant.pk, account.merchant.pk)

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
        # Timeout
        order = WithdrawalOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(order.status, 'timeout')
        # Failed
        order = WithdrawalOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=2),
            time_sent=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(order.status, 'failed')
        # Cancelled
        order = WithdrawalOrderFactory.create()
        self.assertEqual(order.status, 'new')
        order.time_cancelled = timezone.now()
        self.assertEqual(order.status, 'cancelled')

    def test_urls_for_receipts(self):
        order = WithdrawalOrderFactory.create(
            customer_address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE',
            outgoing_tx_id='0' * 64)
        self.assertIn('/wrc/{0}'.format(order.uid), order.receipt_url)

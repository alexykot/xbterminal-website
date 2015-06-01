import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from website.models import (
    User,
    MerchantAccount,
    BTCAccount,
    WithdrawalOrder)
from website.tests.factories import (
    UserFactory,
    MerchantAccountFactory,
    BTCAccountFactory,
    DeviceFactory,
    PaymentOrderFactory,
    WithdrawalOrderFactory)


class UserTestCase(TestCase):

    def test_create_user(self):
        user = User.objects.create(email='test@example.com')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_user_factory(self):
        user = UserFactory.create()
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password('password'))

    def test_get_full_name(self):
        user = UserFactory.create()
        self.assertEqual(user.get_full_name(), user.email)


class MerchantAccountTestCase(TestCase):

    fixtures = ['initial_data.json']

    def create_merchant_account(self):
        user = UserFactory.create()
        merchant = MerchantAccount.objects.create(
            user=user,
            company_name='Test Company',
            contact_first_name='Test',
            contact_last_name='Test',
            contact_email='test@example.net')
        # Check defaults
        self.assertEqual(merchant.country, 'GB')
        self.assertEqual(merchant.language.code, 'en')
        self.assertEqual(merchant.currency.name, 'GBP')
        self.assertEqual(merchant.account_balance, 0)
        self.assertEqual(merchant.account_balance_max, 0)
        self.assertEqual(merchant.payment_processor, 'gocoin')
        self.assertEqual(merchant.verification_status, 'unverified')

    def test_merchant_factory(self):
        merchant = MerchantAccountFactory.create()
        self.assertTrue(merchant.is_profile_complete)
        self.assertIsNotNone(merchant.info)

    def test_is_profile_complete(self):
        merchant = MerchantAccountFactory.create(
            business_address='Test Address',
            town='TestTown',
            post_code='123456',
            contact_phone='')
        self.assertFalse(merchant.is_profile_complete)
        merchant.contact_phone = '123456789'
        merchant.save()
        self.assertTrue(merchant.is_profile_complete)

    def test_get_account_balance(self):
        merchant = MerchantAccountFactory.create()
        self.assertIsNone(merchant.get_account_balance('mainnet'))
        btc_account = BTCAccountFactory.create(
            merchant=merchant, network='mainnet', balance=Decimal('0.5'))
        self.assertEqual(merchant.get_account_balance('mainnet'),
                         Decimal('0.5'))


class BTCAccountTestCase(TestCase):

    fixtures = ['initial_data.json']

    def test_create_btc_account(self):
        merchant = MerchantAccountFactory.create()
        btc_account = BTCAccount.objects.create(merchant=merchant)
        # Check defaults
        self.assertEqual(btc_account.network, 'mainnet')
        self.assertEqual(btc_account.balance, 0)
        self.assertEqual(btc_account.balance_max, 0)
        self.assertIsNone(btc_account.address)

    def test_btc_account_factory(self):
        btc_account = BTCAccountFactory.create()
        self.assertEqual(btc_account.balance, 0)
        self.assertEqual(btc_account.balance_max, 0)
        self.assertIsNone(btc_account.address)


class DeviceTestCase(TestCase):

    fixtures = ['initial_data.json']

    def test_device_factory(self):
        device = DeviceFactory.create()
        self.assertEqual(device.status, 'active')
        self.assertEqual(len(device.key), 8)
        self.assertEqual(device.bitcoin_network, 'mainnet')


class PaymentOrderTestCase(TestCase):

    fixtures = ['initial_data.json']

    def test_payment_order_factory(self):
        payment_order = PaymentOrderFactory.create()
        self.assertEqual(len(payment_order.uid), 6)
        self.assertEqual(payment_order.status, 'new')

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


class WithdrawalOrderTestCase(TestCase):

    fixtures = ['initial_data.json']

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
            exchange_rate=Decimal('10'))
        # Defaults
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
            tx_fee_btc_amount=Decimal('0.0002'))
        self.assertEqual(order.btc_amount, Decimal('0.1002'))

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

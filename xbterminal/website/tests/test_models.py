from decimal import Decimal
from django.conf import settings
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from oauth2_provider.models import Application
from django_fsm import TransitionNotAllowed

from website.models import (
    User,
    Currency,
    UITheme,
    MerchantAccount,
    Account,
    Device,
    DeviceBatch,
    INSTANTFIAT_PROVIDERS)
from website.tests.factories import (
    CurrencyFactory,
    UserFactory,
    MerchantAccountFactory,
    AccountFactory,
    DeviceBatchFactory,
    DeviceFactory,
    ReconciliationTimeFactory)
from operations.tests.factories import PaymentOrderFactory


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
        oauth_apps = Application.objects.filter(user=user)
        self.assertEqual(oauth_apps.count(), 1)
        self.assertEqual(oauth_apps.first().client_id,
                         user.email)

    def test_get_full_name(self):
        user = UserFactory.create()
        self.assertEqual(user.get_full_name(), user.email)


class CurrencyTestCase(TestCase):

    def test_fixtures(self):
        gbp = Currency.objects.get(name='GBP')
        self.assertEqual(gbp.pk, 1)
        usd = Currency.objects.get(name='USD')
        self.assertEqual(usd.prefix, '$')
        self.assertEqual(usd.postfix, '')
        btc = Currency.objects.get(name='BTC')
        self.assertEqual(btc.prefix, '')
        self.assertEqual(btc.postfix, 'BTC')
        tbtc = Currency.objects.get(name='TBTC')
        self.assertEqual(tbtc.prefix, '')
        self.assertEqual(tbtc.postfix, 'tBTC')

    def test_factory(self):
        gbp = CurrencyFactory.create()
        self.assertEqual(gbp.name, 'GBP')
        usd = CurrencyFactory.create(name='USD')
        self.assertEqual(usd.pk, 2)


class UIThemeTestCase(TestCase):

    def test_create_theme(self):
        theme = UITheme.objects.create(name='test')
        self.assertEqual(str(theme), 'test')


class MerchantAccountTestCase(TestCase):

    def test_create_merchant_account(self):
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
        self.assertEqual(merchant.ui_theme.name, 'default')
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
        self.assertIsNone(merchant.get_account_balance('BTC'))
        AccountFactory.create(merchant=merchant,
                              currency__name='BTC',
                              balance=Decimal('0.5'))
        self.assertEqual(merchant.get_account_balance('BTC'),
                         Decimal('0.5'))

    def test_info_new_merchant(self):
        merchant = MerchantAccountFactory.create()
        info = merchant.info
        self.assertEqual(info['name'], merchant.company_name)
        self.assertEqual(info['status'], 'unverified')
        self.assertEqual(info['active'], 0)
        self.assertEqual(info['total'], 0)
        self.assertEqual(info['tx_count'], 0)
        self.assertEqual(info['tx_sum'], 0)

    def test_info_with_payments(self):
        merchant = MerchantAccountFactory.create()
        DeviceFactory.create(merchant=merchant, status='activation')
        active_device = DeviceFactory.create(merchant=merchant,
                                             status='active',
                                             last_activity=timezone.now())
        payments = PaymentOrderFactory.create_batch(
            3, device=active_device, time_notified=timezone.now())

        info = merchant.info
        self.assertEqual(info['active'], 1)
        self.assertEqual(info['total'], 2)
        self.assertEqual(info['tx_count'], len(payments))
        self.assertEqual(info['tx_sum'],
                         sum(p.fiat_amount for p in payments))


class AccountTestCase(TestCase):

    def test_create_btc_account(self):
        merchant = MerchantAccountFactory.create(company_name='mtest')
        currency = CurrencyFactory.create(name='BTC')
        account = Account.objects.create(merchant=merchant,
                                         currency=currency)
        # Check defaults
        self.assertEqual(account.currency.name, 'BTC')
        self.assertEqual(account.balance, 0)
        self.assertEqual(account.balance_max, 0)
        self.assertIsNone(account.bitcoin_address)
        self.assertIsNone(account.instantfiat_provider)
        self.assertIsNone(account.instantfiat_api_key)
        self.assertEqual(str(account), 'mtest (mtest) - BTC')

    def test_factory_btc(self):
        account = AccountFactory.create()
        self.assertEqual(account.currency.name, 'BTC')
        self.assertEqual(account.balance, 0)
        self.assertEqual(account.balance_max, 0)
        self.assertIsNone(account.bitcoin_address)
        self.assertIsNone(account.instantfiat_provider)
        self.assertIsNone(account.instantfiat_api_key)

    def test_factory_gbp(self):
        account = AccountFactory.create(currency__name='GBP')
        self.assertEqual(account.currency.name, 'GBP')
        self.assertEqual(account.balance, 0)
        self.assertEqual(account.balance_max, 0)
        self.assertIsNone(account.bitcoin_address)
        self.assertEqual(account.instantfiat_provider,
                         INSTANTFIAT_PROVIDERS.CRYPTOPAY)
        self.assertIsNotNone(account.instantfiat_api_key)

    def test_unique_together(self):
        merchant = MerchantAccountFactory.create()
        AccountFactory.create(merchant=merchant, currency__name='TBTC')
        with self.assertRaises(IntegrityError):
            AccountFactory.create(merchant=merchant,
                                  currency__name='TBTC')

    def test_bitcoin_network(self):
        account_1 = AccountFactory.create(currency__name='BTC')
        self.assertEqual(account_1.bitcoin_network, 'mainnet')
        account_2 = AccountFactory.create(currency__name='TBTC')
        self.assertEqual(account_2.bitcoin_network, 'testnet')
        account_3 = AccountFactory.create(currency__name='GBP')
        self.assertEqual(account_3.bitcoin_network, 'mainnet')


class DeviceTestCase(TestCase):

    def test_creation(self):
        device = Device.objects.create(
            device_type='hardware',
            name='TEST')
        self.assertIsNone(device.merchant)
        self.assertEqual(device.status, 'registered')
        self.assertEqual(len(device.key), 8)
        self.assertEqual(len(device.activation_code), 6)
        self.assertEqual(device.percent, 100)
        self.assertEqual(device.bitcoin_network, 'mainnet')
        self.assertEqual(device.batch.batch_number,
                         settings.DEFAULT_BATCH_NUMBER)
        self.assertIsNotNone(device.created_at)
        self.assertIsNone(device.last_activity)

    def test_device_factory(self):
        # Registration
        device = DeviceFactory.create(status='registered')
        self.assertIsNone(device.merchant)
        self.assertEqual(device.status, 'registered')
        self.assertEqual(len(device.key), 8)
        self.assertEqual(len(device.activation_code), 6)
        self.assertEqual(device.percent, 0)
        self.assertEqual(device.bitcoin_network, 'mainnet')
        # Activation
        device = DeviceFactory.create(status='activation')
        self.assertIsNotNone(device.merchant)
        self.assertEqual(device.status, 'activation')
        # Active
        device = DeviceFactory.create(status='active')
        self.assertIsNotNone(device.merchant)
        self.assertEqual(device.status, 'active')
        # Without kwargs
        device = DeviceFactory.create()
        self.assertEqual(device.status, 'active')
        # Suspended
        device = DeviceFactory.create(status='suspended')
        self.assertIsNotNone(device.merchant)
        self.assertEqual(device.status, 'suspended')

    def test_transitions(self):
        device = DeviceFactory.create(status='registered')
        self.assertEqual(device.status, 'registered')
        with self.assertRaises(TransitionNotAllowed):
            device.start_activation()
        with self.assertRaises(TransitionNotAllowed):
            device.activate()
        with self.assertRaises(TransitionNotAllowed):
            device.suspend()
        device.merchant = MerchantAccountFactory.create()
        with self.assertRaises(TransitionNotAllowed):
            device.activate()
        device.start_activation()
        self.assertEqual(device.status, 'activation')
        device.activate()
        self.assertEqual(device.status, 'active')
        device.suspend()
        self.assertEqual(device.status, 'suspended')
        device.activate()
        self.assertEqual(device.status, 'active')


class DeviceBatchTestCase(TestCase):

    def test_create(self):
        batch = DeviceBatch.objects.create(size=100)
        self.assertEqual(len(batch.batch_number), 32)
        self.assertIsNotNone(batch.created_at)
        self.assertEqual(batch.size, 100)
        self.assertEqual(str(batch), batch.batch_number)

    def test_factory(self):
        batch = DeviceBatchFactory.create()
        self.assertEqual(len(batch.batch_number), 32)


class ReconciliationTimeTestCase(TestCase):

    def test_reconciliation_time_factory(self):
        rectime = ReconciliationTimeFactory.create()
        self.assertEqual(rectime.email, rectime.device.merchant.user.email)

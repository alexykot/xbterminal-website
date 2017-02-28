# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal
import os

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from constance.test import override_config
from oauth2_provider.models import Application
from django_fsm import TransitionNotAllowed

from website.models import (
    User,
    Currency,
    UITheme,
    MerchantAccount,
    Account,
    Address,
    Transaction,
    Device,
    DeviceBatch,
    INSTANTFIAT_PROVIDERS,
    KYC_DOCUMENT_TYPES)
from website.tests.factories import (
    CurrencyFactory,
    UserFactory,
    MerchantAccountFactory,
    KYCDocumentFactory,
    AccountFactory,
    AddressFactory,
    TransactionFactory,
    DeviceBatchFactory,
    DeviceFactory)
from operations.tests.factories import (
    PaymentOrderFactory,
    WithdrawalOrderFactory)
from operations.blockchain import validate_bitcoin_address


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

    def test_role(self):
        user_1 = UserFactory.create()
        self.assertIsNone(user_1.role)
        user_2 = UserFactory.create(is_staff=True)
        self.assertEqual(user_2.role, 'administrator')
        user_3 = UserFactory.create()
        MerchantAccountFactory.create(user=user_3)
        self.assertEqual(user_3.role, 'merchant')
        user_4 = UserFactory.create(groups__names=['controllers'])
        self.assertEqual(user_4.role, 'controller')


class GroupTestCase(TestCase):

    def test_fixtures(self):
        self.assertTrue(Group.objects.filter(
            name='controllers').exists())


class CurrencyTestCase(TestCase):

    def test_fixture_gbp(self):
        gbp = Currency.objects.get(name='GBP')
        self.assertEqual(gbp.pk, 1)
        self.assertEqual(gbp.prefix, u'£')
        self.assertEqual(gbp.amount_1, Decimal('1.00'))
        self.assertEqual(gbp.amount_2, Decimal('2.50'))
        self.assertEqual(gbp.amount_3, Decimal('10.00'))
        self.assertEqual(gbp.amount_shift, Decimal('0.05'))
        self.assertEqual(gbp.max_payout, 0)

    def test_fixture_usd(self):
        usd = Currency.objects.get(name='USD')
        self.assertEqual(usd.prefix, u'$')
        self.assertEqual(usd.postfix, '')

    def test_fixture_eur(self):
        eur = Currency.objects.get(name='EUR')
        self.assertEqual(eur.prefix, u'€')
        self.assertEqual(eur.postfix, '')

    def test_fixture_btc(self):
        btc = Currency.objects.get(name='BTC')
        self.assertEqual(btc.prefix, '')
        self.assertEqual(btc.postfix, 'BTC')

    def test_fixture_tbtc(self):
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
        self.assertIsNone(merchant.instantfiat_provider)
        self.assertIsNone(merchant.instantfiat_merchant_id)
        self.assertIsNone(merchant.instantfiat_email)
        self.assertIsNone(merchant.instantfiat_api_key)
        self.assertEqual(merchant.verification_status, 'unverified')

    def test_merchant_factory(self):
        merchant = MerchantAccountFactory.create()
        self.assertTrue(merchant.is_profile_complete)
        self.assertIsNotNone(merchant.info)
        self.assertEqual(merchant.currency.name, 'GBP')
        self.assertIsNone(merchant.instantfiat_provider)
        self.assertIsNone(merchant.instantfiat_merchant_id)
        self.assertIsNone(merchant.instantfiat_email)
        self.assertIsNone(merchant.instantfiat_api_key)

    def test_merchant_factory_instantfiat(self):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY)
        self.assertIsNotNone(merchant.instantfiat_provider)
        self.assertEqual(merchant.instantfiat_email,
                         merchant.contact_email)
        self.assertIsNotNone(merchant.instantfiat_api_key)

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

    def test_has_managed_cryptopay_profile(self):
        merchant = MerchantAccountFactory.create()
        self.assertFalse(merchant.has_managed_cryptopay_profile)
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='test')
        self.assertTrue(merchant.has_managed_cryptopay_profile)

    @override_config(CRYPTOPAY_USE_FAKE_EMAIL=True)
    def test_get_cryptopay_email(self):
        merchant = MerchantAccountFactory.create(
            company_name='Test Co Ltd.')
        expected_email = 'merchant-{}-test-co-ltd@xbterminal.io'.format(
            merchant.pk)
        self.assertEqual(merchant.get_cryptopay_email(), expected_email)

    @override_config(CRYPTOPAY_USE_FAKE_EMAIL=False)
    def test_get_cryptopay_email_real(self):
        merchant = MerchantAccountFactory.create(
            company_name='Test Co Ltd.')
        self.assertEqual(merchant.get_cryptopay_email(),
                         merchant.contact_email)

    def test_get_kyc_document(self):
        merchant = MerchantAccountFactory.create()
        document = merchant.get_kyc_document(
            KYC_DOCUMENT_TYPES.ID_FRONT,
            'uploaded')
        self.assertIsNone(document)
        KYCDocumentFactory.create(merchant=merchant)
        document = merchant.get_kyc_document(
            KYC_DOCUMENT_TYPES.ID_FRONT,
            'uploaded')
        self.assertIsNotNone(document)

    def test_info_new_merchant(self):
        merchant = MerchantAccountFactory.create()
        info = merchant.info
        self.assertEqual(info['name'], merchant.company_name)
        self.assertEqual(info['status'], None)
        self.assertEqual(info['active'], 0)
        self.assertEqual(info['total'], 0)
        self.assertEqual(info['tx_count'], 0)
        self.assertEqual(info['tx_sum'], 0)

    def test_info_with_payments_and_managed_profile(self):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='test')
        account = AccountFactory.create(merchant=merchant)
        DeviceFactory.create(merchant=merchant,
                             account=account,
                             status='activation_in_progress')
        active_device = DeviceFactory.create(
            merchant=merchant,
            account=account,
            status='active',
            last_activity=timezone.now())
        payments = PaymentOrderFactory.create_batch(
            3, device=active_device, time_notified=timezone.now())

        info = merchant.info
        self.assertEqual(info['status'], 'unverified')
        self.assertEqual(info['active'], 1)
        self.assertEqual(info['total'], 2)
        self.assertEqual(info['tx_count'], len(payments))
        self.assertEqual(info['tx_sum'],
                         sum(p.fiat_amount for p in payments))


class KYCDocumentTestCase(TestCase):

    def test_factory(self):
        document = KYCDocumentFactory.create()
        self.assertIsNotNone(document.merchant)
        self.assertEqual(document.document_type,
                         KYC_DOCUMENT_TYPES.ID_FRONT)
        self.assertIsNotNone(document.file)
        self.assertIsNotNone(document.uploaded_at)
        self.assertEqual(document.status, 'uploaded')
        self.assertIsNone(document.instantfiat_document_id)
        self.assertIsNone(document.comment)
        self.assertEqual(document.base_name, '1__test.png')
        self.assertEqual(document.original_name, 'test.png')

    def test_delete(self):
        document = KYCDocumentFactory.create(file__name='del.pdf')
        file_path = document.file.path
        self.assertTrue(file_path.endswith('del.pdf'))
        self.assertTrue(os.path.exists(file_path))
        document.delete()
        self.assertFalse(os.path.exists(file_path))


class AccountTestCase(TestCase):

    def test_create_btc_account(self):
        merchant = MerchantAccountFactory.create(company_name='mtest')
        currency = CurrencyFactory.create(name='BTC')
        account = Account.objects.create(merchant=merchant,
                                         currency=currency,
                                         instantfiat=False)
        # Check defaults
        self.assertEqual(account.currency.name, 'BTC')
        self.assertEqual(account.max_payout, 0)
        self.assertEqual(account.balance, 0)
        self.assertFalse(account.instantfiat)
        self.assertIsNone(account.instantfiat_account_id)
        self.assertIsNone(account.bank_account_name)
        self.assertIsNone(account.bank_account_bic)
        self.assertIsNone(account.bank_account_iban)
        self.assertEqual(str(account), 'BTC - 0.00000000')

    def test_factory_btc(self):
        account = AccountFactory.create()
        self.assertEqual(account.currency.name, 'BTC')
        self.assertEqual(account.max_payout, 0)
        self.assertEqual(account.balance, 0)
        self.assertIsNotNone(account.forward_address)
        self.assertFalse(account.instantfiat)
        self.assertIsNone(account.instantfiat_account_id)
        self.assertIsNone(account.bank_account_name)
        self.assertIsNone(account.bank_account_bic)
        self.assertIsNone(account.bank_account_iban)
        self.assertEqual(str(account), 'BTC - 0.00000000')

    def test_factory_gbp(self):
        account = AccountFactory.create(
            currency__name='GBP',
            merchant__instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY)
        self.assertEqual(account.currency.name, 'GBP')
        self.assertEqual(account.max_payout, 0)
        self.assertEqual(account.balance, 0)
        self.assertIsNone(account.forward_address)
        self.assertTrue(account.instantfiat)
        self.assertIsNotNone(account.instantfiat_account_id)
        self.assertIsNone(account.bank_account_name)
        self.assertIsNone(account.bank_account_bic)
        self.assertIsNone(account.bank_account_iban)
        self.assertEqual(str(account), 'GBP - 0.00')

    def test_unique_together_1(self):
        merchant = MerchantAccountFactory.create()
        AccountFactory.create(merchant=merchant, currency__name='TBTC')
        with self.assertRaises(IntegrityError):
            AccountFactory.create(merchant=merchant,
                                  currency__name='TBTC')

    def test_unique_together_2(self):
        merchant = MerchantAccountFactory.create()
        AccountFactory.create(merchant=merchant,
                              instantfiat=False,
                              currency__name='BTC')
        with self.assertRaises(IntegrityError):
            AccountFactory.create(merchant=merchant,
                                  instantfiat=True,
                                  currency__name='BTC')

    def test_bitcoin_network(self):
        account_1 = AccountFactory.create(currency__name='BTC')
        self.assertEqual(account_1.bitcoin_network, 'mainnet')
        account_2 = AccountFactory.create(currency__name='TBTC')
        self.assertEqual(account_2.bitcoin_network, 'testnet')
        account_3 = AccountFactory.create(currency__name='GBP')
        self.assertEqual(account_3.bitcoin_network, 'mainnet')

    def test_balance(self):
        account_1 = AccountFactory.create()
        self.assertEqual(account_1.balance, 0)
        transactions = TransactionFactory.create_batch(
            3, account=account_1)
        self.assertEqual(account_1.balance,
                         sum(t.amount for t in transactions))
        account_2 = AccountFactory.create(balance=Decimal('0.5'))
        self.assertEqual(account_2.balance, Decimal('0.5'))

    def test_balance_confirmed(self):
        account = AccountFactory.create()
        # Payment - forwarded
        TransactionFactory.create(
            payment=PaymentOrderFactory.create(
                time_forwarded=timezone.now()),
            account=account,
            amount=Decimal('0.2'))
        # Payment - confirmed
        TransactionFactory.create(
            payment=PaymentOrderFactory.create(
                time_forwarded=timezone.now(),
                time_confirmed=timezone.now()),
            account=account,
            amount=Decimal('0.3'))
        # Withdrawal - sent
        withdrawal_1 = WithdrawalOrderFactory.create(
            time_sent=timezone.now())
        TransactionFactory.create(
            withdrawal=withdrawal_1,
            account=account,
            amount=Decimal('-0.18'))
        TransactionFactory.create(
            withdrawal=withdrawal_1,
            account=account,
            amount=Decimal('0.03'))
        # Withdrawal - broadcasted
        withdrawal_2 = WithdrawalOrderFactory.create(
            time_sent=timezone.now(),
            time_broadcasted=timezone.now())
        TransactionFactory.create(
            withdrawal=withdrawal_2,
            account=account,
            amount=Decimal('-0.06'))
        TransactionFactory.create(
            withdrawal=withdrawal_2,
            account=account,
            amount=Decimal('0.01'))
        # Without order
        TransactionFactory.create(
            account=account, amount=Decimal('0.13'))
        self.assertEqual(account.balance, Decimal('0.43'))
        self.assertEqual(account.balance_confirmed, Decimal('0.20'))

    def test_balance_min_max(self):
        account_btc = AccountFactory.create(currency__name='BTC',
                                            max_payout=Decimal('0.2'))
        DeviceFactory.create_batch(
            3, merchant=account_btc.merchant, account=account_btc)
        self.assertEqual(account_btc.balance_min, Decimal('0.6'))
        self.assertEqual(account_btc.balance_max, Decimal('1.8'))
        account_gbp = AccountFactory.create(currency__name='GBP')
        DeviceFactory.create_batch(
            3, merchant=account_gbp.merchant, account=account_gbp)
        self.assertEqual(account_gbp.balance_min, 0)
        self.assertEqual(account_gbp.balance_max, 0)

    def test_get_transactions_by_date(self):
        account = AccountFactory.create()
        now = timezone.now()
        range_beg = (now - datetime.timedelta(days=5)).date()
        range_end = (now - datetime.timedelta(days=4)).date()
        TransactionFactory.create(
            account=account,
            created_at=now - datetime.timedelta(days=6))
        TransactionFactory.create(
            account=account,
            created_at=now - datetime.timedelta(days=3))
        TransactionFactory.create(
            created_at=now - datetime.timedelta(days=5))
        tx_1 = TransactionFactory.create(
            account=account,
            created_at=now - datetime.timedelta(days=5))
        tx_2 = TransactionFactory.create(
            account=account,
            created_at=now - datetime.timedelta(days=4))
        transactions = account.get_transactions_by_date(range_beg,
                                                        range_end)
        self.assertEqual(transactions.count(), 2)
        self.assertEqual(transactions[0].pk, tx_1.pk)
        self.assertEqual(transactions[1].pk, tx_2.pk)


class AddressTestCase(TestCase):

    def test_create(self):
        account = AccountFactory.create()
        address_str = '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'
        address = Address.objects.create(
            account=account,
            address=address_str)
        self.assertIsNotNone(address.account)
        self.assertEqual(str(address), address_str)

    def test_factory(self):
        address_main = AddressFactory.create()
        self.assertIsNone(
            validate_bitcoin_address(address_main.address, 'mainnet'))
        address_test = AddressFactory.create(
            account__currency__name='TBTC')
        self.assertIsNone(
            validate_bitcoin_address(address_test.address, 'testnet'))

    def test_unique(self):
        address = AddressFactory.create()
        with self.assertRaises(IntegrityError):
            AddressFactory.create(address=address.address)


class TransactionTestCase(TestCase):

    def test_create(self):
        account = AccountFactory.create()
        transaction = Transaction.objects.create(account=account,
                                                 amount=Decimal('1.5'))
        self.assertIsNone(transaction.payment)
        self.assertIsNone(transaction.withdrawal)
        self.assertEqual(transaction.account.pk, account.pk)
        self.assertIsNone(transaction.instantfiat_tx_id)
        self.assertIsNotNone(transaction.created_at)
        self.assertEqual(str(transaction), str(transaction.pk))

    def test_factory(self):
        transaction = TransactionFactory.create()
        self.assertIsNone(transaction.payment)
        self.assertIsNone(transaction.withdrawal)
        self.assertIsNotNone(transaction.account)
        self.assertGreater(transaction.amount, 0)
        self.assertIsNone(transaction.instantfiat_tx_id)

    def test_unique_together(self):
        account = AccountFactory.create()
        TransactionFactory.create_batch(3, account=account)
        TransactionFactory.create(account=account,
                                  instantfiat_tx_id=1000)
        with self.assertRaises(IntegrityError):
            TransactionFactory.create(account=account,
                                      instantfiat_tx_id=1000)

    def test_tx_hash(self):
        transaction_1 = TransactionFactory.create()
        self.assertIsNone(transaction_1.tx_hash)
        payment_order = PaymentOrderFactory.create(
            outgoing_tx_id='1' * 64)
        transaction_2 = TransactionFactory.create(payment=payment_order)
        self.assertEqual(transaction_2.tx_hash,
                         payment_order.outgoing_tx_id)
        withdrawal_order = WithdrawalOrderFactory.create(
            outgoing_tx_id='2' * 64)
        transaction_3 = TransactionFactory.create(withdrawal=withdrawal_order)
        self.assertEqual(transaction_3.tx_hash,
                         withdrawal_order.outgoing_tx_id)


class DeviceTestCase(TestCase):

    def test_creation(self):
        device = Device.objects.create(
            device_type='hardware',
            name='TEST')
        self.assertIsNone(device.merchant)
        self.assertIsNone(device.account)
        self.assertEqual(device.status, 'registered')
        self.assertEqual(len(device.key), 8)
        self.assertEqual(len(device.activation_code), 6)
        self.assertEqual(device.batch.batch_number,
                         settings.DEFAULT_BATCH_NUMBER)
        self.assertIsNone(device.amount_1)
        self.assertIsNone(device.amount_2)
        self.assertIsNone(device.amount_3)
        self.assertIsNone(device.amount_shift)
        self.assertEqual(device.system_info, {})
        self.assertIsNotNone(device.created_at)
        self.assertIsNone(device.last_activity)

    def test_device_factory(self):
        # Registration
        device = DeviceFactory.create(status='registered')
        self.assertIsNone(device.merchant)
        self.assertIsNone(device.account)
        self.assertEqual(device.status, 'registered')
        self.assertEqual(len(device.key), 8)
        self.assertEqual(len(device.activation_code), 6)
        self.assertIsNone(device.amount_1)
        self.assertIsNone(device.amount_2)
        self.assertIsNone(device.amount_3)
        self.assertIsNone(device.amount_shift)
        self.assertEqual(device.system_info, {})
        # Activation in progress
        device = DeviceFactory.create(status='activation_in_progress')
        self.assertIsNotNone(device.merchant)
        self.assertIsNotNone(device.account)
        self.assertEqual(device.account.merchant.pk, device.merchant.pk)
        self.assertEqual(device.status, 'activation_in_progress')
        self.assertEqual(device.amount_1,
                         device.merchant.currency.amount_1)
        self.assertEqual(device.amount_2,
                         device.merchant.currency.amount_2)
        self.assertEqual(device.amount_3,
                         device.merchant.currency.amount_3)
        self.assertEqual(device.amount_shift,
                         device.merchant.currency.amount_shift)
        # Activation error
        device = DeviceFactory.create(status='activation_error')
        self.assertIsNotNone(device.merchant)
        self.assertIsNotNone(device.account)
        self.assertEqual(device.status, 'activation_error')
        # Active
        device = DeviceFactory.create(status='active')
        self.assertIsNotNone(device.merchant)
        self.assertIsNotNone(device.account)
        self.assertEqual(device.status, 'active')
        # Without kwargs
        device = DeviceFactory.create()
        self.assertEqual(device.status, 'active')
        # Suspended
        device = DeviceFactory.create(status='suspended')
        self.assertIsNotNone(device.merchant)
        self.assertIsNotNone(device.account)
        self.assertEqual(device.status, 'suspended')

    def test_transitions(self):
        device = DeviceFactory.create(status='registered')
        self.assertEqual(device.status, 'registered')
        with self.assertRaises(TransitionNotAllowed):
            device.start_activation()
        with self.assertRaises(TransitionNotAllowed):
            device.set_activation_error()
        with self.assertRaises(TransitionNotAllowed):
            device.activate()
        with self.assertRaises(TransitionNotAllowed):
            device.suspend()
        # Set merchant
        device.merchant = MerchantAccountFactory.create()
        with self.assertRaises(TransitionNotAllowed):
            device.start_activation()
        with self.assertRaises(TransitionNotAllowed):
            device.activate()
        # Set account
        device.account = AccountFactory.create(merchant=device.merchant)
        with self.assertRaises(TransitionNotAllowed):
            device.activate()
        device.start_activation()
        self.assertEqual(device.status, 'activation_in_progress')
        with self.assertRaises(TransitionNotAllowed):
            device.reset_activation()
        device.activate()
        self.assertEqual(device.status, 'active')
        device.suspend()
        self.assertEqual(device.status, 'suspended')
        device.activate()
        self.assertEqual(device.status, 'active')

    def test_transitions_activation_error(self):
        device = DeviceFactory.create(status='registered')
        device.merchant = MerchantAccountFactory.create()
        device.account = AccountFactory.create(merchant=device.merchant)
        device.start_activation()
        self.assertEqual(device.status, 'activation_in_progress')
        device.set_activation_error()
        self.assertEqual(device.status, 'activation_error')
        device.reset_activation()
        self.assertEqual(device.status, 'registered')
        self.assertIsNone(device.merchant)
        self.assertIsNone(device.account)

    def test_bitcoin_network(self):
        device_1 = DeviceFactory.create(status='registered')
        self.assertEqual(device_1.bitcoin_network, 'mainnet')
        device_2 = DeviceFactory.create(status='active')
        self.assertEqual(device_2.bitcoin_network, 'mainnet')
        device_3 = DeviceFactory.create(
            status='active',
            account__currency__name='TBTC')
        self.assertEqual(device_3.bitcoin_network, 'testnet')

    def test_get_transactions(self):
        device = DeviceFactory.create()
        TransactionFactory.create(
            payment=PaymentOrderFactory.create(device=device),
            account=device.account,
            amount=Decimal('0.2'))
        TransactionFactory.create(
            withdrawal=WithdrawalOrderFactory.create(device=device),
            account=device.account,
            amount=Decimal('-0.1'))
        TransactionFactory.create(
            payment=PaymentOrderFactory.create(
                device=None,
                account=device.account),
            account=device.account,
            amount=Decimal('0.5'))
        transactions = device.get_transactions()
        self.assertEqual(transactions[0].amount, Decimal('0.2'))
        self.assertEqual(transactions[1].amount, Decimal('-0.1'))

    def test_get_transactions_by_date(self):
        device = DeviceFactory.create()
        now = timezone.now()
        date_1 = (now - datetime.timedelta(days=5)).date()
        date_2 = (now - datetime.timedelta(days=4)).date()
        TransactionFactory.create(
            payment=PaymentOrderFactory.create(device=device),
            account=device.account,
            created_at=now - datetime.timedelta(days=6))
        TransactionFactory.create(
            payment=PaymentOrderFactory.create(device=device),
            account=device.account,
            created_at=now - datetime.timedelta(days=3))
        tx_1 = TransactionFactory.create(
            payment=PaymentOrderFactory.create(device=device),
            account=device.account,
            created_at=now - datetime.timedelta(days=5))
        tx_2 = TransactionFactory.create(
            payment=PaymentOrderFactory.create(device=device),
            account=device.account,
            created_at=now - datetime.timedelta(days=4))
        transactions = device.get_transactions_by_date(date_1, date_2)
        self.assertEqual(transactions.count(), 2)
        self.assertEqual(transactions[0].pk, tx_1.pk)
        self.assertEqual(transactions[1].pk, tx_2.pk)

    def test_is_online(self):
        device = DeviceFactory.create()
        self.assertIsNone(device.last_activity)
        self.assertIs(device.is_online(), False)
        device.last_activity = (timezone.now() -
                                datetime.timedelta(minutes=5))
        self.assertIs(device.is_online(), False)
        device.last_activity = (timezone.now() -
                                datetime.timedelta(minutes=1))
        self.assertIs(device.is_online(), True)


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

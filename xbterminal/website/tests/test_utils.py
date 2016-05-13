from mock import patch
from django.conf import settings
from django.core import mail
from django.test import TestCase

from website.models import INSTANTFIAT_PROVIDERS
from website.utils.accounts import (
    check_managed_accounts,
    create_managed_accounts,
    update_managed_accounts)
from website.utils.email import send_error_message
from website.tests.factories import (
    MerchantAccountFactory,
    AccountFactory)
from operations.tests.factories import (
    PaymentOrderFactory,
    WithdrawalOrderFactory)


class AccountsUtilsTestCase(TestCase):

    def test_check_managed_accounts(self):
        merchant = MerchantAccountFactory.create()
        self.assertFalse(check_managed_accounts(merchant))
        AccountFactory.create(
            merchant=merchant,
            currency__name='GBP',
            instantfiat_merchant_id='test')
        self.assertFalse(check_managed_accounts(merchant))
        AccountFactory.create(
            merchant=merchant,
            currency__name='USD',
            instantfiat_merchant_id='test')
        self.assertFalse(check_managed_accounts(merchant))
        AccountFactory.create(
            merchant=merchant,
            currency__name='EUR',
            instantfiat_merchant_id='test')
        self.assertTrue(check_managed_accounts(merchant))

    @patch('website.utils.accounts.cryptopay.list_accounts')
    def test_create_managed_accounts(self, list_mock):
        list_mock.return_value = [
            {'id': 'a1', 'currency': 'BTC'},
            {'id': 'a2', 'currency': 'GBP'},
            {'id': 'a3', 'currency': 'USD'},
            {'id': 'a4', 'currency': 'EUR'},
        ]
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_api_key='test-key')
        create_managed_accounts(merchant)
        self.assertEqual(merchant.account_set.count(), 4)
        account_btc = merchant.account_set.get(currency__name='BTC',
                                               instantfiat=True)
        self.assertEqual(account_btc.instantfiat_account_id, 'a1')
        account_eur = merchant.account_set.get(currency__name='EUR',
                                               instantfiat=True)
        self.assertEqual(account_eur.instantfiat_account_id, 'a4')

    @patch('website.utils.accounts.cryptopay.list_accounts')
    def test_update_managed_accounts(self, list_mock):
        list_mock.return_value = [
            {'id': 'a1', 'currency': 'BTC'},
            {'id': 'a2', 'currency': 'GBP'},
            {'id': 'a3', 'currency': 'USD'},
            {'id': 'a4', 'currency': 'EUR'},
        ]
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_api_key='test-key')
        AccountFactory.create(merchant=merchant,
                              currency__name='EUR',
                              instantfiat=True,
                              instantfiat_account_id='test')
        update_managed_accounts(merchant)
        self.assertEqual(merchant.account_set.count(), 4)
        account_btc = merchant.account_set.get(currency__name='BTC',
                                               instantfiat=True)
        self.assertEqual(account_btc.instantfiat_account_id, 'a1')
        account_eur = merchant.account_set.get(currency__name='EUR',
                                               instantfiat=True)
        self.assertEqual(account_eur.instantfiat_account_id, 'a4')


class EmailUtilsTestCase(TestCase):

    def test_error_message_payment(self):
        order = PaymentOrderFactory.create()
        send_error_message(order=order)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to,
                         settings.CONTACT_EMAIL_RECIPIENTS)

    def test_error_message_withdrawal(self):
        order = WithdrawalOrderFactory.create()
        send_error_message(order=order)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to,
                         settings.CONTACT_EMAIL_RECIPIENTS)

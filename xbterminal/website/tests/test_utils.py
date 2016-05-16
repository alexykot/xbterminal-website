from decimal import Decimal

from mock import patch
from django.conf import settings
from django.core import mail
from django.test import TestCase

from website.models import INSTANTFIAT_PROVIDERS
from website.utils.accounts import (
    create_managed_accounts,
    update_managed_accounts,
    update_balances)
from website.utils.email import send_error_message
from website.tests.factories import (
    MerchantAccountFactory,
    AccountFactory,
    TransactionFactory)
from operations.tests.factories import (
    PaymentOrderFactory,
    WithdrawalOrderFactory)


class AccountsUtilsTestCase(TestCase):

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

    @patch('website.utils.accounts.cryptopay.list_transactions')
    def test_update_balances(self, list_mock):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_api_key='test-key')
        account = AccountFactory.create(merchant=merchant,
                                        currency=merchant.currency,
                                        instantfiat=True,
                                        instantfiat_account_id='test-id')
        TransactionFactory.create(account=account,
                                  instantfiat_tx_id=115,
                                  amount=Decimal('1.25'))
        self.assertEqual(account.balance, Decimal('1.25'))
        list_mock.return_value = [
            {'id': 115, 'amount': '1.25'},
            {'id': 117, 'amount': '0.65'},
            {'id': 120, 'amount': '-0.85'},
        ]
        update_balances(merchant)
        self.assertEqual(account.transaction_set.count(), 3)
        self.assertEqual(account.balance, Decimal('1.05'))
        self.assertEqual(list_mock.call_args[0][0], 'test-id')
        self.assertEqual(list_mock.call_args[0][1], 'test-key')


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

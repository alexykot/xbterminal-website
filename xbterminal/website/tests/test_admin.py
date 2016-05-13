import mock
from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from website.tests.factories import (
    CurrencyFactory,
    MerchantAccountFactory,
    AccountFactory)
from website.models import MerchantAccount, Account, INSTANTFIAT_PROVIDERS
from website.admin import MerchantAccountAdmin, AccountAdmin


class MerchantAccountAdminTestCase(TestCase):

    @mock.patch('website.admin.cryptopay.set_password')
    def test_reset_cryptopay_password(self, set_password_mock):
        ma = MerchantAccountAdmin(MerchantAccount, AdminSite())
        message_user_mock = mock.Mock()
        ma.message_user = message_user_mock
        merchant = MerchantAccountFactory.create()
        AccountFactory.create(
            merchant=merchant,
            currency__name='GBP',
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='test-id')
        request = mock.Mock()
        queryset = MerchantAccount.objects.filter(pk=merchant.pk)
        ma.reset_cryptopay_password(request, queryset)
        self.assertTrue(message_user_mock.called)
        self.assertTrue(set_password_mock.called)
        self.assertEqual(set_password_mock.call_args[0][0], 'test-id')
        password = set_password_mock.call_args[0][1]
        self.assertEqual(len(password), 16)
        self.assertIn(password, message_user_mock.call_args[0][1])


class AccountAdminTestCase(TestCase):

    def setUp(self):
        self.ma = AccountAdmin(Account, AdminSite())

    def test_create_instantfiat(self):
        merchant = MerchantAccountFactory.create()
        form_cls = self.ma.get_form(mock.Mock(), None)
        data = {
            'merchant': merchant.pk,
            'currency': merchant.currency.pk,
            'balance_max': '0.00',
            'bitcoin_address': '',
            'forward_address': '',
            'instantfiat': True,
            'instantfiat_account_id': 'test',
        }
        form = form_cls(data=data)
        self.assertTrue(form.is_valid())
        account = form.save()
        self.assertEqual(account.instantfiat_account_id,
                         data['instantfiat_account_id'])

    def test_create_instantfiat_error(self):
        merchant = MerchantAccountFactory.create()
        form_cls = self.ma.get_form(mock.Mock(), None)
        data = {
            'merchant': merchant.pk,
            'currency': merchant.currency.pk,
            'balance_max': '0.00',
            'bitcoin_address': '',
            'forward_address': '',
            'instantfiat': True,
        }
        form = form_cls(data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['instantfiat_account_id'][0],
                         'This field is required.')

    def test_create_btc_error(self):
        merchant = MerchantAccountFactory.create()
        form_cls = self.ma.get_form(mock.Mock(), None)
        btc = CurrencyFactory.create(name='BTC')
        data = {
            'merchant': merchant.pk,
            'currency': btc.pk,
            'balance_max': '0.00',
            'bitcoin_address': '',
            'forward_address': '',
            'instantfiat': False,
        }
        form = form_cls(data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['forward_address'][0],
                         'This field is required.')

    def test_update_btc(self):
        account = AccountFactory.create(
            bitcoin_address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        data = {
            'merchant': account.merchant.pk,
            'currency': account.currency.pk,
            'balance_max': '1.00',
            'bitcoin_address': '',
            'forward_address': '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE',
            'instantfiat': False,
        }
        form_cls = self.ma.get_form(mock.Mock(), account)
        form = form_cls(data=data, instance=account)
        self.assertTrue(form.is_valid())
        account_updated = form.save()
        self.assertEqual(account_updated.pk, account.pk)
        self.assertEqual(account_updated.bitcoin_address,
                         account.bitcoin_address)

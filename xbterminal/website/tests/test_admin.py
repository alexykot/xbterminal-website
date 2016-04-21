import mock
from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from website.tests.factories import (
    MerchantAccountFactory,
    AccountFactory)
from website.models import Account, INSTANTFIAT_PROVIDERS
from website.admin import AccountAdmin


class AccountAdminTestCase(TestCase):

    def setUp(self):
        self.ma = AccountAdmin(Account, AdminSite())

    def test_create_gbp(self):
        merchant = MerchantAccountFactory.create()
        form_cls = self.ma.get_form(mock.Mock(), None)
        data = {
            'merchant': merchant.pk,
            'currency': merchant.currency.pk,
            'balance': '0.00',
            'balance_max': '0.00',
            'bitcoin_address': '',
            'instantfiat_provider': INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            'instantfiat_api_key': 'test',
        }
        form = form_cls(data=data)
        self.assertTrue(form.is_valid())
        account = form.save()
        self.assertEqual(account.instantfiat_provider,
                         INSTANTFIAT_PROVIDERS.CRYPTOPAY)

    def test_create_gbp_error(self):
        merchant = MerchantAccountFactory.create()
        form_cls = self.ma.get_form(mock.Mock(), None)
        data = {
            'merchant': merchant.pk,
            'currency': merchant.currency.pk,
            'balance': '0.00',
            'balance_max': '0.00',
            'bitcoin_address': '',
            'instantfiat_provider': '',
            'instantfiat_api_key': '',
        }
        form = form_cls(data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['instantfiat_provider'][0],
                         'This field is required.')

    def test_update_btc(self):
        account = AccountFactory.create(
            bitcoin_address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        data = {
            'merchant': account.merchant.pk,
            'currency': account.currency.pk,
            'balance': '0.00',
            'balance_max': '1.00',
            'bitcoin_address': '',
        }
        form_cls = self.ma.get_form(mock.Mock(), account)
        form = form_cls(data=data, instance=account)
        self.assertTrue(form.is_valid())
        account_updated = form.save()
        self.assertEqual(account_updated.pk, account.pk)
        self.assertEqual(account_updated.bitcoin_address,
                         account.bitcoin_address)

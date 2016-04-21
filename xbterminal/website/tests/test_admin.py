import mock
from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from website.tests.factories import AccountFactory
from website.models import Account
from website.admin import AccountAdmin


class AccountAdminTestCase(TestCase):

    def setUp(self):
        self.ma = AccountAdmin(Account, AdminSite())

    def test_form(self):
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

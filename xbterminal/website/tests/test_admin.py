import mock
from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from website.tests.factories import BTCAccountFactory
from website.models import BTCAccount
from website.admin import BTCAccountAdmin


class BTCAccountAdminTestCase(TestCase):

    def setUp(self):
        self.ma = BTCAccountAdmin(BTCAccount, AdminSite())

    def test_form(self):
        account = BTCAccountFactory.create(
            address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        data = {
            'merchant': account.merchant.pk,
            'network': account.network,
            'balance': '0.00',
            'balance_max': '1.00',
            'address': '',
        }
        form_cls = self.ma.get_form(mock.Mock(), account)
        form = form_cls(data=data)
        self.assertTrue(form.is_valid())
        account_updated = form.save()
        self.assertEqual(account_updated.address, account.address)

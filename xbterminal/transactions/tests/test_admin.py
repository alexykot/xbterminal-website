from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from mock import Mock

from transactions.models import Deposit
from transactions.admin import DepositAdmin
from transactions.tests.factories import DepositFactory


class DepositAdminTestCase(TestCase):

    def setUp(self):
        self.ma = DepositAdmin(Deposit, AdminSite())

    def test_form(self):
        deposit = DepositFactory.create()
        form_cls = self.ma.get_form(Mock(), deposit)
        form = form_cls(data={}, instance=deposit)
        self.assertIs(form.is_valid(), True)
        self.assertEqual(form.cleaned_data, {})
        deposit_updated = form.save()
        self.assertEqual(deposit_updated.deposit_address,
                         deposit.deposit_address)

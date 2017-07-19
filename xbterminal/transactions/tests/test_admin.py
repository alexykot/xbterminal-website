from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from mock import patch, Mock

from transactions.models import Deposit
from transactions.admin import DepositAdmin
from transactions.tests.factories import DepositFactory


class DepositAdminTestCase(TestCase):

    def setUp(self):
        self.ma = DepositAdmin(Deposit, AdminSite())
        self.ma.message_user = Mock()

    def test_form(self):
        deposit = DepositFactory.create()
        form_cls = self.ma.get_form(Mock(), deposit)
        form = form_cls(data={}, instance=deposit)
        self.assertIs(form.is_valid(), True)
        self.assertEqual(form.cleaned_data, {})
        deposit_updated = form.save()
        self.assertEqual(deposit_updated.deposit_address,
                         deposit.deposit_address)

    @patch('transactions.admin.check_deposit_confirmation')
    def test_check_confirmation(self, check_mock):
        check_mock.return_value = True
        deposit_1 = DepositFactory()
        deposit_2 = DepositFactory(unconfirmed=True)
        self.ma.check_confirmation(
            Mock(),
            Deposit.objects.filter(pk__in=[deposit_1.pk, deposit_2.pk]))

        self.assertEqual(check_mock.call_count, 1)
        self.assertEqual(check_mock.call_args[0][0], deposit_2)
        self.assertEqual(self.ma.message_user.call_count, 1)
        self.assertEqual(
            self.ma.message_user.call_args[0][1],
            'Deposit "{0}" is confirmed.'.format(deposit_2.pk))

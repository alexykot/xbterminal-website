from decimal import Decimal
from django.test import TestCase

from website.tests.factories import DeviceFactory
from api.forms import WithdrawalForm


class WithdrawalFormTestCase(TestCase):

    def test_form(self):
        device = DeviceFactory.create()
        form_data = {
            'device': device.key,
            'amount': '0.50',
        }
        form = WithdrawalForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['device'].pk, device.pk)
        self.assertEqual(form.cleaned_data['amount'], Decimal('0.5'))

    def test_invalid_device_key(self):
        form_data = {
            'device': 'invalidkey',
            'amount': '0.50',
        }
        form = WithdrawalForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.error_message,
                         'Device - invalid device key')

    def test_invalid_amount(self):
        device = DeviceFactory.create()
        form_data = {
            'device': device.key,
            'amount': '0.00',
        }
        form = WithdrawalForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.error_message,
                         'Amount - ensure this value '
                         'is greater than or equal to 0.01.')

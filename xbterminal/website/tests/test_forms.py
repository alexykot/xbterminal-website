from mock import patch
from django.test import TestCase
from django.core import mail

from oauth2_provider.models import Application
from website.forms import (
    MerchantRegistrationForm,
    DeviceForm,
    DeviceActivationForm)
from website.tests.factories import DeviceFactory


class MerchantRegistrationFormTestCase(TestCase):

    def test_init(self):
        form = MerchantRegistrationForm()
        regtype_choices = dict(form.fields['regtype'].choices)
        self.assertIn('default', regtype_choices)
        self.assertIn('terminal', regtype_choices)
        self.assertIn('web', regtype_choices)

    @patch('website.forms.gocoin.create_merchant')
    def test_valid_data(self, gocoin_mock):
        gocoin_mock.return_value = 'x' * 32
        form_data = {
            'regtype': 'default',
            'company_name': 'Test Company',
            'business_address': 'Test Address',
            'town': 'Test Town',
            'country': 'GB',
            'post_code': '123456',
            'contact_first_name': 'Test',
            'contact_last_name': 'Test',
            'contact_email': 'test@example.net',
            'contact_phone': '+123456789',
        }
        form = MerchantRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        merchant = form.save()
        self.assertEqual(merchant.company_name, form_data['company_name'])
        self.assertEqual(merchant.user.email, form_data['contact_email'])
        self.assertEqual(merchant.language.code, 'en')
        self.assertEqual(merchant.currency.name, 'GBP')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], form_data['contact_email'])
        self.assertTrue(gocoin_mock.called)
        oauth_app = Application.objects.get(user=merchant.user)
        self.assertEqual(oauth_app.client_id, form_data['contact_email'])

    def test_required(self):
        form = MerchantRegistrationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('regtype', form.errors)
        self.assertIn('company_name', form.errors)
        self.assertIn('business_address', form.errors)
        self.assertIn('town', form.errors)
        self.assertIn('country', form.errors)
        self.assertIn('post_code', form.errors)
        self.assertIn('contact_first_name', form.errors)
        self.assertIn('contact_last_name', form.errors)
        self.assertIn('contact_email', form.errors)
        self.assertIn('contact_phone', form.errors)


class DeviceFormTestCase(TestCase):

    def test_valid_data(self):
        form_data = {
            'device_type': 'hardware',
            'name': 'Terminal',
            'payment_processing': 'keep',
            'percent': '0',
            'bitcoin_address': '1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6',
        }
        form = DeviceForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.device_type_verbose(), 'Terminal')
        device = form.save(commit=False)
        self.assertEqual(device.device_type, 'hardware')
        self.assertEqual(device.name, form_data['name'])
        self.assertEqual(device.payment_processing, 'keep')

    def test_required(self):
        form = DeviceForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('device_type', form.errors)
        self.assertIn('name', form.errors)
        self.assertIn('payment_processing', form.errors)
        self.assertIn('percent', form.errors)


class DeviceActivationFormTestCase(TestCase):

    def test_valid_code(self):
        device = DeviceFactory.create(status='activation')
        form_data = {
            'activation_code': device.activation_code,
        }
        form = DeviceActivationForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.device.pk, device.pk)

    def test_required(self):
        form = DeviceActivationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('activation_code', form.errors)

    def test_already_activated(self):
        device = DeviceFactory.create(status='active')
        form_data = {
            'activation_code': device.activation_code,
        }
        form = DeviceActivationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Invalid activation code.',
                      form.errors['activation_code'])

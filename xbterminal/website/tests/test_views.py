import json
from django.core.urlresolvers import reverse
from django.conf import settings
from django.test import TestCase
from django.core import mail
from mock import patch

from website.tests.factories import MerchantAccountFactory


class RegistrationViewTestCase(TestCase):

    fixtures = ['initial_data.json']

    def setUp(self):
        self.url = reverse('website:registration')

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/registration.html')

    @patch('website.forms.gocoin.create_merchant')
    def test_post(self, gocoin_mock):
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
        response = self.client.post(self.url, data=form_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['result'], 'ok')

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to[0],
                         form_data['contact_email'])
        self.assertEqual(mail.outbox[1].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])


class CreateDeviceViewTestCase(TestCase):

    fixtures = ['initial_data.json']

    def setUp(self):
        self.url = reverse('website:create_device')
        self.merchant = MerchantAccountFactory.create()

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cabinet/device_form.html')
        self.assertEqual(response.context['form'].initial['device_type'],
                         'hardware')

    def test_post(self):
        self.client.login(username=self.merchant.user.email,
                          password='password')
        form_data = {
            'device_type': 'hardware',
            'name': 'Terminal',
            'payment_processing': 'full',
            'percent': '100',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 302)

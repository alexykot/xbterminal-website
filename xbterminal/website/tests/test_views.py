import json
from django.core.urlresolvers import reverse
from django.conf import settings
from django.test import TestCase
from django.core import mail
from django.utils import timezone
from mock import patch

from website.tests.factories import (
    MerchantAccountFactory,
    DeviceFactory)
from operations.tests.factories import PaymentOrderFactory


class RegistrationViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:registration')

    def test_get_default(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/registration.html')
        form = response.context['form']
        self.assertEqual(form.initial['regtype'], 'default')

    @patch('website.forms.preorder')
    def test_get_terminal(self, preorder_mock):
        response = self.client.get(self.url, {'regtype': 'terminal'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/registration.html')
        form = response.context['form']
        self.assertEqual(form.initial['regtype'], 'terminal')

    @patch('website.forms.gocoin.create_merchant')
    def test_post_default(self, gocoin_mock):
        gocoin_mock.return_value = 'x' * 32
        form_data = {
            'regtype': 'default',
            'company_name': 'Test Company 1',
            'business_address': 'Test Address',
            'town': 'Test Town',
            'country': 'GB',
            'post_code': '123456',
            'contact_first_name': 'Test',
            'contact_last_name': 'Test',
            'contact_email': 'test1@example.net',
            'contact_phone': '+123456789',
        }
        response = self.client.post(self.url, data=form_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['result'], 'ok')

        self.assertTrue(gocoin_mock.called)
        merchant = gocoin_mock.call_args[0][0]
        self.assertEqual(merchant.company_name, form_data['company_name'])
        self.assertEqual(merchant.user.email,
                         form_data['contact_email'])
        self.assertEqual(merchant.device_set.count(), 0)

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to[0],
                         form_data['contact_email'])
        self.assertEqual(mail.outbox[1].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])

    @patch('website.forms.gocoin.create_merchant')
    @patch('website.forms.preorder.create_invoice')
    def test_post_terminal(self, create_invoice_mock, gocoin_mock):
        gocoin_mock.return_value = 'x' * 32
        form_data = {
            'regtype': 'terminal',
            'company_name': 'Test Company 2',
            'business_address': 'Test Address',
            'town': 'Test Town',
            'country': 'GB',
            'post_code': '123456',
            'contact_first_name': 'Test',
            'contact_last_name': 'Test',
            'contact_email': 'test2@example.net',
            'contact_phone': '+123456789',
            # Preorder form
            'quantity': 2,
            'payment_method': 'bitcoin',
        }
        response = self.client.post(self.url, data=form_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['result'], 'ok')

        self.assertTrue(gocoin_mock.called)
        merchant = gocoin_mock.call_args[0][0]
        self.assertEqual(merchant.company_name, form_data['company_name'])

        self.assertTrue(create_invoice_mock.called)
        order = create_invoice_mock.call_args[0][0]
        self.assertEqual(order.merchant.pk, merchant.pk)
        self.assertEqual(order.quantity,
                         form_data['quantity'])
        self.assertEqual(order.payment_method,
                         form_data['payment_method'])

        self.assertEqual(merchant.device_set.count(),
                         form_data['quantity'])
        device = merchant.device_set.first()
        self.assertEqual(device.device_type, 'hardware')
        self.assertEqual(device.status, 'active')

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to[0],
                         form_data['contact_email'])
        self.assertEqual(mail.outbox[1].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])

    @patch('website.forms.gocoin.create_merchant')
    def test_post_web(self, gocoin_mock):
        gocoin_mock.return_value = 'x' * 32
        form_data = {
            'regtype': 'web',
            'company_name': 'Test Company 3',
            'business_address': 'Test Address',
            'town': 'Test Town',
            'country': 'GB',
            'post_code': '123456',
            'contact_first_name': 'Test',
            'contact_last_name': 'Test',
            'contact_email': 'test3@example.net',
            'contact_phone': '+123456789',
        }
        response = self.client.post(self.url, data=form_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['result'], 'ok')

        self.assertTrue(gocoin_mock.called)
        merchant = gocoin_mock.call_args[0][0]
        self.assertEqual(merchant.company_name, form_data['company_name'])

        self.assertEqual(merchant.device_set.count(), 1)
        device = merchant.device_set.first()
        self.assertEqual(device.device_type, 'web')
        self.assertEqual(device.status, 'active')

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to[0],
                         form_data['contact_email'])
        self.assertEqual(mail.outbox[1].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])


class CreateDeviceViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:create_device')

    def test_get(self):
        merchant = MerchantAccountFactory.create()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cabinet/device_form.html')
        self.assertEqual(response.context['form'].initial['device_type'],
                         'hardware')

    def test_post(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        self.assertEqual(merchant.device_set.count(), 0)
        form_data = {
            'device_type': 'hardware',
            'name': 'Terminal',
            'payment_processing': 'full',
            'percent': '100',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(merchant.device_set.count(), 1)
        device = merchant.device_set.first()
        self.assertEqual(device.status, 'active')
        self.assertEqual(device.device_type, 'hardware')
        self.assertEqual(device.name, 'Terminal')
        self.assertEqual(device.payment_processing, 'full')


class UpdateDeviceView(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_get(self):
        device = DeviceFactory.create(merchant=self.merchant)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:device',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_get_not_activated(self):
        device = DeviceFactory.create(status='activation')
        device.merchant = self.merchant
        device.save()
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:device',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class ActivateDeviceViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:activate_device')

    def test_get(self):
        merchant = MerchantAccountFactory.create()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cabinet/activation.html')

    def test_post_valid_code(self):
        merchant = MerchantAccountFactory.create()
        self.assertEqual(merchant.device_set.count(), 0)
        self.client.login(username=merchant.user.email,
                          password='password')

        device = DeviceFactory.create(status='activation')
        form_data = {
            'activation_code': device.activation_code,
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(merchant.device_set.count(), 1)
        active_device = merchant.device_set.first()
        self.assertEqual(active_device.status, 'active')
        self.assertEqual(active_device.merchant.pk, merchant.pk)

    def test_post_error(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')

        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cabinet/activation.html')
        self.assertIn('activation_code',
                      response.context['form'].errors)


class ReconciliationViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        device = DeviceFactory.create(merchant=self.merchant)
        orders = PaymentOrderFactory.create_batch(
            5,
            device=device,
            time_finished=timezone.now())
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:reconciliation',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cabinet/reconciliation.html')
        payments = response.context['daily_payments_info']
        self.assertEqual(payments[0]['count'], len(orders))
        self.assertEqual(payments[0]['btc_amount'],
                         sum(po.btc_amount for po in orders))
        self.assertEqual(payments[0]['fiat_amount'],
                         sum(po.fiat_amount for po in orders))
        self.assertEqual(payments[0]['instantfiat_fiat_amount'],
                         sum(po.instantfiat_fiat_amount for po in orders))


class ReportViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        device = DeviceFactory.create(merchant=self.merchant)
        payment_order = PaymentOrderFactory.create(
            device=device,
            time_finished=timezone.now())
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:report',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Content-Disposition'))


class ReceiptsViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        device = DeviceFactory.create(merchant=self.merchant)
        payment_order = PaymentOrderFactory.create(
            device=device,
            time_finished=timezone.now())
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:receipts',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Content-Disposition'))


class SendAllToEmailViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        device = DeviceFactory.create(merchant=self.merchant)
        payment_order = PaymentOrderFactory.create(
            device=device,
            time_finished=timezone.now())
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:send_all_to_email',
                      kwargs={'device_key': device.key})
        form_data = {
            'email': 'test@example.net',
            'date': payment_order.time_finished.strftime('%Y-%m-%d'),
        }
        response = self.client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], form_data['email'])

    @patch('website.utils.create_html_message')
    def test_data(self, create_mock):
        device = DeviceFactory.create(merchant=self.merchant)
        orders = PaymentOrderFactory.create_batch(
            5,
            device=device,
            time_finished=timezone.now())
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:send_all_to_email',
                      kwargs={'device_key': device.key})
        form_data = {
            'email': 'test@example.net',
            'date': orders[0].time_finished.strftime('%Y-%m-%d'),
        }
        self.client.post(url, data=form_data)
        self.assertTrue(create_mock.called)
        context = create_mock.call_args[0][2]
        self.assertEqual(context['device'].pk, device.pk)
        self.assertEqual(context['btc_amount'],
                         sum(po.btc_amount for po in orders))
        self.assertEqual(context['fiat_amount'],
                         sum(po.fiat_amount for po in orders))


class PaymentViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        device = DeviceFactory.create(merchant=self.merchant)
        url = reverse('website:payment',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payment/payment.html')

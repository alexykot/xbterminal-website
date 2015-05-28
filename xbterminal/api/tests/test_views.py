from decimal import Decimal
import json
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone
from mock import patch, Mock

from website.models import PaymentOrder
from website.tests.factories import DeviceFactory, PaymentOrderFactory


class DeviceSettingsViewTestCase(TestCase):

    fixtures = ['initial_data.json']

    def test_settings(self):
        device = DeviceFactory.create()
        url = reverse('api:device', kwargs={'key': device.key})
        response = self.client.get(url)
        data = json.loads(response.content)
        self.assertEqual(data['MERCHANT_NAME'],
                         device.merchant.company_name)
        self.assertEqual(data['MERCHANT_DEVICE_NAME'], device.name)
        self.assertEqual(data['MERCHANT_LANGUAGE'], 'en')
        self.assertEqual(data['MERCHANT_CURRENCY'], 'GBP')
        self.assertEqual(data['MERCHANT_CURRENCY_SIGN_POSTFIX'], '')
        self.assertEqual(data['MERCHANT_CURRENCY_SIGN_PREFIX'], u'\u00A3')
        self.assertEqual(data['OUTPUT_DEC_FRACTIONAL_SPLIT'], '.')
        self.assertEqual(data['OUTPUT_DEC_THOUSANDS_SPLIT'], ',')
        self.assertEqual(data['BITCOIN_NETWORK'], 'mainnet')


class PaymentInitViewTestCase(TestCase):

    fixtures = ['initial_data.json']

    def setUp(self):
        self.url = reverse('api:payment_init')

    @patch('api.views.payment.tasks.prepare_payment')
    def test_payment_website(self, prepare_mock):
        device = DeviceFactory.create()
        fiat_amount = 0.5
        btc_amount = 0.00329
        exchange_rate = 0.152
        payment_order = PaymentOrderFactory.create(
            device=device,
            fiat_amount=Decimal(fiat_amount),
            btc_amount=Decimal(btc_amount),
            effective_exchange_rate=Decimal(exchange_rate))
        prepare_mock.return_value = payment_order

        form_data = {
            'device_key': device.key,
            'amount': fiat_amount,
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['fiat_amount'], fiat_amount)
        self.assertEqual(data['btc_amount'], btc_amount)
        self.assertEqual(data['exchange_rate'], exchange_rate)
        self.assertIn('check_url', data)
        self.assertIn('payment_uri', data)
        self.assertIn('qr_code_src', data)

        payment_order = PaymentOrder.objects.get(uid=payment_order.uid)
        self.assertGreater(len(payment_order.request), 0)

    @patch('api.views.payment.tasks.prepare_payment')
    def test_payment_terminal(self, prepare_mock):
        device = DeviceFactory.create()
        fiat_amount = 0.5
        btc_amount = 0.00329
        exchange_rate = 0.152
        bluetooth_mac = '12:34:56:78:9A:BC'
        payment_order = PaymentOrderFactory.create(
            device=device,
            fiat_amount=Decimal(fiat_amount),
            btc_amount=Decimal(btc_amount),
            effective_exchange_rate=Decimal(exchange_rate))
        prepare_mock.return_value = payment_order

        form_data = {
            'device_key': device.key,
            'amount': fiat_amount,
            'bt_mac': bluetooth_mac,
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['fiat_amount'], fiat_amount)
        self.assertEqual(data['btc_amount'], btc_amount)
        self.assertEqual(data['exchange_rate'], exchange_rate)
        self.assertIn('check_url', data)
        self.assertIn('payment_uri', data)
        self.assertEqual(data['payment_uid'], payment_order.uid)
        self.assertIn('payment_request', data)

    def test_invalid_amount(self):
        device = DeviceFactory.create()
        form_data = {
            'device_key': device.key,
            'amount': 'aaa',
        }
        response = self.client.post(self.url, form_data)
        data = json.loads(response.content)
        self.assertIn('amount', data['errors'])

    def test_invalid_device_key(self):
        form_data = {
            'device_key': 'invalidkey',
            'amount': '0.5',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 404)


class PaymentRequestViewTestCase(TestCase):

    fixtures = ['initial_data.json']

    def test_payment_request(self):
        data = '009A8B'.decode('hex')
        payment_order = PaymentOrderFactory.create(
            request=data)
        url = reverse('api:payment_request',
                      kwargs={'payment_uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'],
                         'application/bitcoin-paymentrequest')
        self.assertEqual(response.content, data)


class PaymentResponseViewTestCase(TestCase):

    fixtures = ['initial_data.json']

    def setUp(self):
        self.payment_order = PaymentOrderFactory.create()
        self.url = reverse(
            'api:payment_response',
            kwargs={'payment_uid': self.payment_order.uid})

    @patch('api.views.payment.tasks.parse_payment')
    def test_payment_response(self, parse_mock):
        parse_mock.return_value = 'test'
        data = '009A8B'.decode('hex')
        response = self.client.post(
            self.url, data,
            content_type='application/bitcoin-payment')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'],
                         'application/bitcoin-paymentack')
        self.assertEqual(response.content, 'test')
        self.assertTrue(parse_mock.called)

    def test_invalid_headers(self):
        data = '009A8B'.decode('hex')
        response = self.client.post(
            self.url, data,
            content_type='application/octet-stream')
        self.assertEqual(response.status_code, 400)


class PaymentCheckViewTestCase(TestCase):

    fixtures = ['initial_data.json']

    def test_payment_not_finished(self):
        payment_order = PaymentOrderFactory.create()
        url = reverse('api:payment_check',
                      kwargs={'payment_uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['paid'], 0)

    def test_payment_finished(self):
        payment_order = PaymentOrderFactory.create(
            time_forwarded=timezone.now())
        self.assertIsNone(payment_order.time_finished)
        url = reverse('api:payment_check',
                      kwargs={'payment_uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['paid'], 1)
        self.assertIn('receipt_url', data)
        self.assertIn('qr_code_src', data)
        payment_order = PaymentOrder.objects.get(uid=payment_order.uid)
        self.assertIsNotNone(payment_order.time_finished)


class ReceiptViewTestCase(TestCase):

    fixtures = ['initial_data.json']

    @patch('api.shortcuts.get_template')
    def test_receipt(self, get_template_mock):
        template_mock = Mock(**{
            'render.return_value': 'test',
        })
        get_template_mock.return_value = template_mock
        payment_order = PaymentOrderFactory.create(
            time_finished=timezone.now())
        url = reverse('api:receipt',
                      kwargs={'payment_uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(template_mock.render.called)

    def test_payment_not_finished(self):
        payment_order = PaymentOrderFactory.create()
        url = reverse('api:receipt',
                      kwargs={'payment_uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

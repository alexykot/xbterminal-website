from decimal import Decimal
import json

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone
from mock import patch, Mock
from rest_framework import status

from operations import exceptions
from operations.models import PaymentOrder
from operations.tests.factories import PaymentOrderFactory
from website.models import Device
from website.tests.factories import (
    MerchantAccountFactory,
    DeviceFactory)


class DevicesViewTestCase(TestCase):

    def _get_access_token(self, user):
        token_url = reverse('token')
        response = self.client.post(token_url, data={
            'grant_type': 'password',
            'username': user.email,
            'password': 'password',
            'client_id': user.email,
            'client_secret': 'secret',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['token_type'], 'Bearer')
        return data['access_token']

    def test_list(self):
        merchant = MerchantAccountFactory.create()
        device = DeviceFactory.create(merchant=merchant)
        access_token = self._get_access_token(merchant.user)
        # Get devices
        devices_url = reverse('api:devices')
        response = self.client.get(
            devices_url,
            AUTHORIZATION='Bearer {}'.format(access_token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], device.name)

    def test_create_device(self):
        merchant = MerchantAccountFactory.create()
        access_token = self._get_access_token(merchant.user)
        devices_url = reverse('api:devices')
        response = self.client.post(
            devices_url,
            data={'name': 'NewDevice'},
            AUTHORIZATION='Bearer {}'.format(access_token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['name'], 'NewDevice')
        self.assertIn('key', data)
        self.assertEqual(data['percent'], 100.0)
        self.assertEqual(data['type'], 'mobile')
        self.assertFalse(data['online'])
        device = Device.objects.get(key=data['key'])
        self.assertEqual(device.status, 'active')
        self.assertEqual(device.merchant.pk, merchant.pk)
        self.assertIsNone(device.account)


class DeviceSettingsViewTestCase(TestCase):

    def test_settings(self):
        device = DeviceFactory.create()
        url = reverse('api:device', kwargs={'key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
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

    def test_not_active(self):
        device = DeviceFactory.create(status='registered')
        url = reverse('api:device', kwargs={'key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PaymentInitViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('api:payment_init')

    @patch('api.views_v1.operations.payment.prepare_payment')
    def test_payment_website(self, prepare_mock):
        device = DeviceFactory.create()
        fiat_amount = 10
        btc_amount = 0.05
        exchange_rate = 200
        payment_order = PaymentOrderFactory.create(
            device=device,
            fiat_amount=Decimal(fiat_amount),
            merchant_btc_amount=Decimal('0.0499'),
            tx_fee_btc_amount=Decimal('0.0001'))
        prepare_mock.return_value = payment_order

        form_data = {
            'device_key': device.key,
            'amount': fiat_amount,
            'qr_code': 'true',
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

    @patch('api.views_v1.operations.payment.prepare_payment')
    def test_payment_terminal(self, prepare_mock):
        device = DeviceFactory.create(long_key=True)
        fiat_amount = 10
        btc_amount = 0.05
        exchange_rate = 200
        bluetooth_mac = '12:34:56:78:9A:BC'
        payment_order = PaymentOrderFactory.create(
            device=device,
            fiat_amount=Decimal(fiat_amount),
            merchant_btc_amount=Decimal('0.0499'),
            tx_fee_btc_amount=Decimal('0.0001'))
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
        self.assertIn('qr_code_src', data)

    def test_invalid_amount(self):
        device = DeviceFactory.create()
        form_data = {
            'device_key': device.key,
            'amount': 'aaa',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        self.assertIn('amount', data['errors'])

    def test_invalid_device_key(self):
        form_data = {
            'device_key': 'invalidkey',
            'amount': '0.5',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_not_active(self):
        device = DeviceFactory.create(status='activation')
        form_data = {
            'device_key': device.key,
            'amount': '0.5',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.views_v1.operations.payment.prepare_payment')
    def test_payment_error(self, prepare_mock):
        prepare_mock.side_effect = exceptions.PaymentError
        device = DeviceFactory.create(long_key=True)
        fiat_amount = 10
        bluetooth_mac = '12:34:56:78:9A:BC'
        form_data = {
            'device_key': device.key,
            'amount': fiat_amount,
            'bt_mac': bluetooth_mac,
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Payment error')


class PaymentRequestViewTestCase(TestCase):

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

    def setUp(self):
        self.payment_order = PaymentOrderFactory.create()
        self.url = reverse(
            'api:payment_response',
            kwargs={'payment_uid': self.payment_order.uid})

    @patch('api.views_v1.operations.payment.parse_payment')
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

    def test_payment_not_notified(self):
        payment_order = PaymentOrderFactory.create()
        url = reverse('api:payment_check',
                      kwargs={'payment_uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['paid'], 0)

    def test_payment_notified(self):
        payment_order = PaymentOrderFactory.create(
            time_forwarded=timezone.now())
        self.assertIsNone(payment_order.time_notified)
        url = reverse('api:payment_check',
                      kwargs={'payment_uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['paid'], 1)
        self.assertIn('receipt_url', data)
        self.assertIn('qr_code_src', data)
        payment_order = PaymentOrder.objects.get(uid=payment_order.uid)
        self.assertIsNotNone(payment_order.time_notified)


class ReceiptViewTestCase(TestCase):

    @patch('api.utils.pdf.get_template')
    def test_payment_order(self, get_template_mock):
        template_mock = Mock(**{
            'render.return_value': 'test',
        })
        get_template_mock.return_value = template_mock
        payment_order = PaymentOrderFactory.create(
            time_notified=timezone.now())
        url = reverse('api:receipt',
                      kwargs={'order_uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(template_mock.render.called)

    def test_payment_not_notified(self):
        payment_order = PaymentOrderFactory.create()
        url = reverse('api:receipt',
                      kwargs={'order_uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

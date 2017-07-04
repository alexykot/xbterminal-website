from decimal import Decimal
import json

from django.core.urlresolvers import reverse
from django.test import TestCase

from mock import patch, Mock
from rest_framework import status

from operations import exceptions
from transactions.tests.factories import DepositFactory
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
        self.assertEqual(data['percent'], 0.0)
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
        self.assertEqual(data['SERIAL_NUMBER'], '0000')

    def test_not_active(self):
        device = DeviceFactory.create(status='registered')
        url = reverse('api:device', kwargs={'key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PaymentInitViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('api:payment_init')

    @patch('api.views_v1.prepare_deposit')
    def test_payment_website(self, prepare_mock):
        device = DeviceFactory.create()
        fiat_amount = 10
        btc_amount = 0.05
        exchange_rate = 200
        prepare_mock.return_value = deposit = DepositFactory(
            device=device,
            amount=Decimal(fiat_amount),
            merchant_coin_amount=Decimal('0.0499'),
            fee_coin_amount=Decimal('0.0001'))

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
        self.assertEqual(data['payment_uid'], deposit.uid)
        self.assertIn('qr_code_src', data)

    @patch('api.views_v1.prepare_deposit')
    def test_payment_terminal(self, prepare_mock):
        device = DeviceFactory.create(long_key=True)
        fiat_amount = 10
        btc_amount = 0.05
        exchange_rate = 200
        bluetooth_mac = '12:34:56:78:9A:BC'
        prepare_mock.return_value = deposit = DepositFactory(
            device=device,
            amount=Decimal(fiat_amount),
            merchant_coin_amount=Decimal('0.0499'),
            fee_coin_amount=Decimal('0.0001'))

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
        self.assertEqual(data['payment_uid'], deposit.uid)
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
        device = DeviceFactory.create(status='activation_in_progress')
        form_data = {
            'device_key': device.key,
            'amount': '0.5',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.views_v1.prepare_deposit')
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

    @patch('transactions.models.create_payment_request')
    def test_payment_request(self, create_mock):
        create_mock.return_value = data = '009A8B'.decode('hex')
        deposit = DepositFactory()
        url = reverse('api:payment_request',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'],
                         'application/bitcoin-paymentrequest')
        self.assertEqual(response.content, data)


class PaymentResponseViewTestCase(TestCase):

    def setUp(self):
        self.deposit = DepositFactory()
        self.url = reverse(
            'api:payment_response',
            kwargs={'uid': self.deposit.uid})

    @patch('api.views_v1.handle_bip70_payment')
    def test_payment_response(self, handle_mock):
        handle_mock.return_value = 'test'
        data = '009A8B'.decode('hex')
        response = self.client.post(
            self.url, data,
            content_type='application/bitcoin-payment')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'],
                         'application/bitcoin-paymentack')
        self.assertEqual(response.content, 'test')
        self.assertIs(handle_mock.called, True)

    def test_invalid_headers(self):
        data = '009A8B'.decode('hex')
        response = self.client.post(
            self.url, data,
            content_type='application/octet-stream')
        self.assertEqual(response.status_code, 400)


class PaymentCheckViewTestCase(TestCase):

    def test_payment_not_notified(self):
        deposit = DepositFactory()
        url = reverse('api:payment_check',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['paid'], 0)

    def test_payment_notified(self):
        deposit = DepositFactory(broadcasted=True)
        self.assertIsNone(deposit.time_notified)
        url = reverse('api:payment_check',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['paid'], 1)
        self.assertIn('receipt_url', data)
        self.assertIn('qr_code_src', data)
        deposit.refresh_from_db()
        self.assertIsNotNone(deposit.time_notified)


class ReceiptViewTestCase(TestCase):

    @patch('api.utils.pdf.get_template')
    def test_payment_order(self, get_template_mock):
        get_template_mock.return_value = template_mock = Mock(**{
            'render.return_value': 'test',
        })
        deposit = DepositFactory(notified=True)
        url = reverse('api:receipt',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(template_mock.render.called)

    def test_payment_not_notified(self):
        deposit = DepositFactory()
        url = reverse('api:receipt',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

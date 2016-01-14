from decimal import Decimal
import json
import hashlib
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone
from mock import patch, Mock
from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import status

from operations.models import PaymentOrder
from operations.tests.factories import (
    PaymentOrderFactory,
    WithdrawalOrderFactory)
from website.models import Device
from website.tests.factories import (
    MerchantAccountFactory,
    DeviceBatchFactory,
    DeviceFactory)
from api.views import WithdrawalViewSet
from api.utils.crypto import create_test_signature, create_test_public_key


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

    @patch('api.views.operations.payment.prepare_payment')
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

    @patch('api.views.operations.payment.prepare_payment')
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
        data = json.loads(response.content)
        self.assertIn('amount', data['errors'])

    def test_invalid_device_key(self):
        form_data = {
            'device_key': 'invalidkey',
            'amount': '0.5',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 404)

    def test_not_active(self):
        device = DeviceFactory.create(status='activation')
        form_data = {
            'device_key': device.key,
            'amount': '0.5',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


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

    @patch('api.views.operations.payment.parse_payment')
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

    @patch('api.utils.pdf.get_template')
    def test_payment_order(self, get_template_mock):
        template_mock = Mock(**{
            'render.return_value': 'test',
        })
        get_template_mock.return_value = template_mock
        payment_order = PaymentOrderFactory.create(
            time_finished=timezone.now())
        url = reverse('api:receipt',
                      kwargs={'order_uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(template_mock.render.called)

    def test_payment_not_finished(self):
        payment_order = PaymentOrderFactory.create()
        url = reverse('api:receipt',
                      kwargs={'order_uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @patch('api.utils.pdf.get_template')
    def test_withdrawal_order(self, get_template_mock):
        template_mock = Mock(**{
            'render.return_value': 'test',
        })
        get_template_mock.return_value = template_mock
        withdrawal_order = WithdrawalOrderFactory.create(
            time_completed=timezone.now())
        url = reverse('api:receipt',
                      kwargs={'order_uid': withdrawal_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(template_mock.render.called)

    def test_withdrawal_not_finished(self):
        withdrawal_order = WithdrawalOrderFactory.create()
        url = reverse('api:receipt',
                      kwargs={'order_uid': withdrawal_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class WithdrawalViewSetTestCase(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    @patch('api.views.withdrawal.prepare_withdrawal')
    def test_create_order(self, prepare_mock):
        device = DeviceFactory.create()
        order = WithdrawalOrderFactory.create(
            device=device, fiat_amount=Decimal('1.00'))
        prepare_mock.return_value = order

        view = WithdrawalViewSet.as_view(actions={'post': 'create'})
        form_data = {
            'device': device.key,
            'amount': '1.00',
        }
        url = reverse('api:v2:withdrawal-list')
        request = self.factory.post(url, form_data, format='json')
        device.api_key, request.META['HTTP_X_SIGNATURE'] = \
            create_test_signature(request.body)
        device.save()

        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uid'], order.uid)
        self.assertEqual(response.data['btc_amount'],
                         str(order.btc_amount))
        self.assertEqual(response.data['exchange_rate'],
                         str(order.effective_exchange_rate))
        self.assertEqual(response.data['status'], 'new')

    def test_create_order_error(self):
        form_data = {
            'device': 'invalid_key',
            'amount': '1.00',
        }
        url = reverse('api:v2:withdrawal-list')
        response = self.client.post(url, form_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'],
                         'Device - invalid device key')

    def test_device_not_active(self):
        device = DeviceFactory.create(status='activation')
        form_data = {
            'device': device.key,
            'amount': '1.00',
        }
        url = reverse('api:v2:withdrawal-list')
        response = self.client.post(url, form_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'],
                         'Device - invalid device key')

    def test_invalid_signature(self):
        device = DeviceFactory.create()

        view = WithdrawalViewSet.as_view(actions={'post': 'create'})
        form_data = {
            'device': device.key,
            'amount': '1.00',
        }
        url = reverse('api:v2:withdrawal-list')
        request = self.factory.post(url, form_data, format='json')
        device.api_key, signature = create_test_signature(request.body)
        device.save()
        request.META['HTTP_X_SIGNATURE'] = 'invalid_sig'

        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('api.views.withdrawal.send_transaction')
    def test_confirm(self, send_mock):
        order = WithdrawalOrderFactory.create()

        view = WithdrawalViewSet.as_view(
            actions={'post': 'confirm'})
        form_data = {'address': '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'}
        url = reverse('api:v2:withdrawal-confirm', kwargs={'uid': order.uid})
        request = self.factory.post(url, form_data, format='json')
        order.device.api_key, request.META['HTTP_X_SIGNATURE'] = \
            create_test_signature(request.body)
        order.device.save()

        response = view(request, uid=order.uid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        self.assertTrue(send_mock.called)

    def test_check(self):
        order = WithdrawalOrderFactory.create(time_sent=timezone.now())
        url = reverse('api:v2:withdrawal-detail', kwargs={'uid': order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'sent')

        order.time_broadcasted = timezone.now()
        order.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')


class DeviceViewSetTestCase(APITestCase):

    @patch('api.serializers.Salt')
    def test_create(self, salt_cls_mock):
        salt_cls_mock.return_value = salt_mock = Mock(**{
            'check_fingerprint.return_value': True,
        })
        batch = DeviceBatchFactory.create()
        device_key = hashlib.sha256('createDevice').hexdigest()
        form_data = {
            'batch': batch.batch_number,
            'key': device_key,
            'api_key': create_test_public_key(),
            'salt_fingerprint': 'test',
        }
        url = reverse('api:v2:device-list')

        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('activation_code', response.data)

        device = Device.objects.get(
            activation_code=response.data['activation_code'])
        self.assertEqual(device.key, device_key)
        self.assertEqual(device.status, 'registered')
        self.assertEqual(device.batch.pk, batch.pk)

    @patch('api.serializers.Salt')
    def test_create_errors(self, salt_cls_mock):
        url = reverse('api:v2:device-list')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('batch', response.data['errors'])
        self.assertIn('key', response.data['errors'])
        self.assertIn('api_key', response.data['errors'])

    def test_retrieve_registered(self):
        device = DeviceFactory.create(status='registered')
        url = reverse('api:v2:device-detail',
                      kwargs={'key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'registered')
        self.assertEqual(response.data['language']['code'], 'en')
        self.assertEqual(response.data['currency']['name'], 'GBP')

    def test_retrieve_activation(self):
        device = DeviceFactory.create(status='activation')
        url = reverse('api:v2:device-detail',
                      kwargs={'key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'activation_in_progress')

    def test_retrieve_active(self):
        device = DeviceFactory.create(status='active')
        url = reverse('api:v2:device-detail',
                      kwargs={'key': device.key})
        self.assertFalse(device.is_online())
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'active')

        updated_device = Device.objects.get(pk=device.pk)
        self.assertTrue(updated_device.is_online())

    def test_retrieve_suspended(self):
        device = DeviceFactory.create(status='suspended')
        url = reverse('api:v2:device-detail',
                      kwargs={'key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DeviceBatchViewSetTestCase(APITestCase):

    @patch('api.views.config')
    def test_current(self, config_mock):
        batch = DeviceBatchFactory.create()
        config_mock.CURRENT_BATCH_NUMBER = batch.batch_number
        url = reverse('api:v2:batch-current')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'],
                         'application/gzip')
        self.assertEqual(response['Content-Disposition'],
                         'filename="batch.tar.gz"')

    @patch('api.views.config')
    def test_current_not_found(self, config_mock):
        config_mock.CURRENT_BATCH_NUMBER = settings.DEFAULT_BATCH_NUMBER
        url = reverse('api:v2:batch-current')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

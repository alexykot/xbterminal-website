import datetime
from decimal import Decimal
import hashlib

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone
from mock import patch, Mock
from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import status

from api.views_v2 import WithdrawalViewSet
from api.utils.crypto import create_test_signature, create_test_public_key
from operations import exceptions
from operations.models import PaymentOrder
from operations.tests.factories import (
    PaymentOrderFactory,
    WithdrawalOrderFactory)
from website.models import Device
from website.tests.factories import DeviceFactory, DeviceBatchFactory


class PaymentViewSetTestCase(APITestCase):

    @patch('api.views_v2.operations.payment.prepare_payment')
    def test_create_from_website(self, prepare_mock):
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

        url = reverse('api:v2:payment-list')
        form_data = {
            'device_key': device.key,
            'amount': fiat_amount,
            'qr_code': 'true',
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['fiat_amount'], fiat_amount)
        self.assertEqual(data['btc_amount'], btc_amount)
        self.assertEqual(data['exchange_rate'], exchange_rate)
        self.assertIn('check_url', data)
        self.assertIn('payment_uri', data)
        self.assertIn('qr_code_src', data)

        payment_order = PaymentOrder.objects.get(uid=payment_order.uid)
        self.assertGreater(len(payment_order.request), 0)

    @patch('api.views_v2.operations.payment.prepare_payment')
    def test_create_from_terminal(self, prepare_mock):
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

        url = reverse('api:v2:payment-list')
        form_data = {
            'device_key': device.key,
            'amount': fiat_amount,
            'bt_mac': bluetooth_mac,
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['fiat_amount'], fiat_amount)
        self.assertEqual(data['btc_amount'], btc_amount)
        self.assertEqual(data['exchange_rate'], exchange_rate)
        self.assertIn('check_url', data)
        self.assertIn('payment_uri', data)
        self.assertEqual(data['payment_uid'], payment_order.uid)
        self.assertIn('payment_request', data)
        self.assertIn('qr_code_src', data)

    def test_create_invalid_amount(self):
        device = DeviceFactory.create()
        url = reverse('api:v2:payment-list')
        form_data = {
            'device_key': device.key,
            'amount': 'aaa',
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.data
        self.assertIn('amount', data['errors'])

    def test_create_invalid_device_key(self):
        url = reverse('api:v2:payment-list')
        form_data = {
            'device_key': 'invalidkey',
            'amount': '0.5',
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_not_active(self):
        device = DeviceFactory.create(status='activation')
        url = reverse('api:v2:payment-list')
        form_data = {
            'device_key': device.key,
            'amount': '0.5',
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.views_v2.operations.payment.prepare_payment')
    def test_payment_error(self, prepare_mock):
        prepare_mock.side_effect = exceptions.PaymentError
        device = DeviceFactory.create(long_key=True)
        fiat_amount = 10
        bluetooth_mac = '12:34:56:78:9A:BC'
        url = reverse('api:v2:payment-list')
        form_data = {
            'device_key': device.key,
            'amount': fiat_amount,
            'bt_mac': bluetooth_mac,
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Payment error')

    def test_retrieve_not_notified(self):
        payment_order = PaymentOrderFactory.create()
        url = reverse('api:v2:payment-detail',
                      kwargs={'uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['paid'], 0)

    def test_retrieve_notified(self):
        payment_order = PaymentOrderFactory.create(
            time_forwarded=timezone.now())
        self.assertIsNone(payment_order.time_notified)
        url = reverse('api:v2:payment-detail',
                      kwargs={'uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['paid'], 1)
        payment_order.refresh_from_db()
        self.assertIsNotNone(payment_order.time_notified)

    def test_cancel(self):
        order = PaymentOrderFactory.create()
        url = reverse('api:v2:payment-cancel', kwargs={'uid': order.uid})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')

    def test_cancel_already_received(self):
        order = PaymentOrderFactory.create(time_recieved=timezone.now())
        url = reverse('api:v2:payment-cancel', kwargs={'uid': order.uid})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')

    def test_cancel_already_forwarded(self):
        order = PaymentOrderFactory.create(
            time_recieved=timezone.now(),
            time_forwarded=timezone.now())
        url = reverse('api:v2:payment-cancel', kwargs={'uid': order.uid})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_payment_request(self):
        data = '009A8B'.decode('hex')
        payment_order = PaymentOrderFactory.create(
            request=data)
        url = reverse('api:v2:payment-request',
                      kwargs={'uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'],
                         'application/bitcoin-paymentrequest')
        self.assertEqual(response.content, data)

    def test_payment_request_timeout(self):
        order = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(order.status, 'timeout')
        url = reverse('api:v2:payment-request', kwargs={'uid': order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_payment_request_cancelled(self):
        order = PaymentOrderFactory.create(
            time_cancelled=timezone.now())
        self.assertEqual(order.status, 'cancelled')
        url = reverse('api:v2:payment-request', kwargs={'uid': order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.views_v2.operations.payment.parse_payment')
    def test_payment_response(self, parse_mock):
        payment_order = PaymentOrderFactory.create()
        parse_mock.return_value = 'test'
        data = '009A8B'.decode('hex')
        url = reverse(
            'api:v2:payment-response',
            kwargs={'uid': payment_order.uid})
        response = self.client.post(
            url, data,
            content_type='application/bitcoin-payment')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'],
                         'application/bitcoin-paymentack')
        self.assertEqual(response.content, 'test')
        self.assertTrue(parse_mock.called)

    def test_payment_response_invalid_headers(self):
        payment_order = PaymentOrderFactory.create()
        data = '009A8B'.decode('hex')
        url = reverse(
            'api:v2:payment-response',
            kwargs={'uid': payment_order.uid})
        response = self.client.post(
            url, data,
            content_type='application/octet-stream')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payment_response_already_received(self):
        order = PaymentOrderFactory.create(time_recieved=timezone.now())
        url = reverse('api:v2:payment-response', kwargs={'uid': order.uid})
        response = self.client.post(
            url, '',
            content_type='application/bitcoin-payment')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.utils.pdf.get_template')
    def test_receipt(self, get_template_mock):
        get_template_mock.return_value = template_mock = Mock(**{
            'render.return_value': 'test',
        })
        order = PaymentOrderFactory.create(
            time_notified=timezone.now())
        url = reverse('api:v2:payment-receipt',
                      kwargs={'uid': order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(template_mock.render.called)

    def test_receipt_not_completed(self):
        order = PaymentOrderFactory.create()
        url = reverse('api:v2:payment-receipt',
                      kwargs={'uid': order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.utils.pdf.get_template')
    def test_receipt_short(self, get_template_mock):
        get_template_mock.return_value = Mock(**{
            'render.return_value': 'test',
        })
        order = PaymentOrderFactory.create(
            time_notified=timezone.now())
        url = reverse('api:short:payment-receipt',
                      kwargs={'uid': order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_receipt_short_post(self):
        order = PaymentOrderFactory.create(
            time_notified=timezone.now())
        url = reverse('api:short:payment-receipt',
                      kwargs={'uid': order.uid})
        response = self.client.post(url, {})
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)


class WithdrawalViewSetTestCase(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    @patch('api.views_v2.withdrawal.prepare_withdrawal')
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

    @patch('api.views_v2.withdrawal.send_transaction')
    def test_confirm(self, send_mock):
        def write_time_sent(order, address):
            order.time_sent = timezone.now()
            order.save()
        send_mock.side_effect = write_time_sent

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
        self.assertEqual(response.data['status'], 'sent')
        self.assertTrue(send_mock.called)

    def test_confirm_already_sent(self):
        order = WithdrawalOrderFactory.create(time_sent=timezone.now())
        view = WithdrawalViewSet.as_view(actions={'post': 'confirm'})
        form_data = {'address': '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'}
        url = reverse('api:v2:withdrawal-confirm', kwargs={'uid': order.uid})
        request = self.factory.post(url, form_data, format='json')
        order.device.api_key, request.META['HTTP_X_SIGNATURE'] = \
            create_test_signature(request.body)
        order.device.save()

        response = view(request, uid=order.uid)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel(self):
        order = WithdrawalOrderFactory.create()
        view = WithdrawalViewSet.as_view(actions={'post': 'cancel'})
        url = reverse('api:v2:withdrawal-cancel', kwargs={'uid': order.uid})
        request = self.factory.post(url, {}, format='json')
        order.device.api_key, request.META['HTTP_X_SIGNATURE'] = \
            create_test_signature(request.body)
        order.device.save()

        response = view(request, uid=order.uid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')

    def test_cancel_not_new(self):
        order = WithdrawalOrderFactory.create(time_sent=timezone.now())
        view = WithdrawalViewSet.as_view(actions={'post': 'cancel'})
        url = reverse('api:v2:withdrawal-cancel', kwargs={'uid': order.uid})
        request = self.factory.post(url, {}, format='json')
        order.device.api_key, request.META['HTTP_X_SIGNATURE'] = \
            create_test_signature(request.body)
        order.device.save()

        response = view(request, uid=order.uid)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

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

    @patch('api.utils.pdf.get_template')
    def test_receipt(self, get_template_mock):
        get_template_mock.return_value = template_mock = Mock(**{
            'render.return_value': 'test',
        })
        order = WithdrawalOrderFactory.create(
            time_completed=timezone.now())
        url = reverse('api:v2:withdrawal-receipt',
                      kwargs={'uid': order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(template_mock.render.called)

    def test_receipt_not_completed(self):
        order = WithdrawalOrderFactory.create()
        url = reverse('api:v2:withdrawal-receipt',
                      kwargs={'uid': order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.utils.pdf.get_template')
    def test_receipt_short(self, get_template_mock):
        get_template_mock.return_value = Mock(**{
            'render.return_value': 'test',
        })
        order = WithdrawalOrderFactory.create(
            time_completed=timezone.now())
        url = reverse('api:short:withdrawal-receipt',
                      kwargs={'uid': order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_receipt_short_post(self):
        order = WithdrawalOrderFactory.create(
            time_completed=timezone.now())
        url = reverse('api:short:withdrawal-receipt',
                      kwargs={'uid': order.uid})
        response = self.client.post(url, {})
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)


class DeviceViewSetTestCase(APITestCase):

    @patch('api.serializers.Salt')
    def test_create(self, salt_cls_mock):
        salt_cls_mock.return_value = Mock(**{
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

    def test_confirm_activation(self):
        device = DeviceFactory.create(status='activation')
        url = reverse('api:v2:device-confirm-activation',
                      kwargs={'key': device.key})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        device_updated = Device.objects.get(pk=device.pk)
        self.assertEqual(device_updated.status, 'active')

    def test_confirm_activation_already_active(self):
        device = DeviceFactory.create(status='active')
        url = reverse('api:v2:device-confirm-activation',
                      kwargs={'key': device.key})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DeviceBatchViewSetTestCase(APITestCase):

    @patch('api.views_v2.config')
    def test_current(self, config_mock):
        batch = DeviceBatchFactory.create()
        config_mock.CURRENT_BATCH_NUMBER = batch.batch_number
        url = reverse('api:v2:batch-current')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, batch.batch_number)

    @patch('api.views_v2.config')
    def test_current_not_found(self, config_mock):
        config_mock.CURRENT_BATCH_NUMBER = settings.DEFAULT_BATCH_NUMBER
        url = reverse('api:v2:batch-current')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

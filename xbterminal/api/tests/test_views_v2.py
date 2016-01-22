from decimal import Decimal
from django.core.urlresolvers import reverse
from django.utils import timezone
from mock import patch, Mock
from rest_framework.test import APITestCase
from rest_framework import status

from operations.models import PaymentOrder
from operations.tests.factories import PaymentOrderFactory
from website.tests.factories import DeviceFactory


class PaymentViewSetTestCase(APITestCase):

    @patch('api.views.operations.payment.prepare_payment')
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

    @patch('api.views.operations.payment.prepare_payment')
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

    def test_retrieve_not_finished(self):
        payment_order = PaymentOrderFactory.create()
        url = reverse('api:v2:payment-detail',
                      kwargs={'uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['paid'], 0)

    def test_retrieve_finished(self):
        payment_order = PaymentOrderFactory.create(
            time_forwarded=timezone.now())
        self.assertIsNone(payment_order.time_finished)
        url = reverse('api:v2:payment-detail',
                      kwargs={'uid': payment_order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['paid'], 1)
        self.assertIn('receipt_url', data)
        self.assertIn('qr_code_src', data)
        payment_order = PaymentOrder.objects.get(uid=payment_order.uid)
        self.assertIsNotNone(payment_order.time_finished)

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

    @patch('api.views.operations.payment.parse_payment')
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

    @patch('api.utils.pdf.get_template')
    def test_receipt(self, get_template_mock):
        get_template_mock.return_value = template_mock = Mock(**{
            'render.return_value': 'test',
        })
        order = PaymentOrderFactory.create(
            time_finished=timezone.now())
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
            time_finished=timezone.now())
        url = reverse('api:short:payment-receipt',
                      kwargs={'uid': order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_receipt_short_post(self):
        order = PaymentOrderFactory.create(
            time_finished=timezone.now())
        url = reverse('api:short:payment-receipt',
                      kwargs={'uid': order.uid})
        response = self.client.post(url, {})
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)

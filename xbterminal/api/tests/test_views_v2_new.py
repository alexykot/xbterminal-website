from decimal import Decimal

from django.core.urlresolvers import reverse
from django.test import TestCase

from mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from api.views_v2_new import DepositSerializer
from operations.exceptions import PaymentError
from transactions.tests.factories import DepositFactory
from website.tests.factories import AccountFactory, DeviceFactory


class DepositSerializerTestCase(TestCase):

    def test_serialization(self):
        deposit = DepositFactory(received=True)
        data = DepositSerializer(deposit).data
        self.assertEqual(data['uid'], deposit.uid)
        self.assertEqual(data['fiat_amount'].rstrip('0'),
                         str(deposit.amount).rstrip('0'))
        self.assertEqual(data['btc_amount'], str(deposit.coin_amount))
        self.assertEqual(data['paid_btc_amount'],
                         str(deposit.paid_coin_amount))
        self.assertEqual(data['exchange_rate'],
                         str(deposit.effective_exchange_rate))
        self.assertEqual(data['status'], deposit.status)


class DepositViewSetTestCase(APITestCase):

    @patch('api.views_v2_new.prepare_deposit')
    def test_create_from_website(self, prepare_mock):
        device = DeviceFactory()
        amount = 10
        prepare_mock.return_value = deposit = DepositFactory(
            account=device.account,
            device=device,
            amount=Decimal(amount),
            merchant_coin_amount=Decimal('0.0499'),
            fee_coin_amount=Decimal('0.0001'))

        url = reverse('api:v2:deposit-list')
        form_data = {
            'device': device.key,
            'amount': amount,
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['uid'], deposit.uid)
        self.assertEqual(data['fiat_amount'], '10.00')
        self.assertEqual(data['btc_amount'], '0.05000000')
        self.assertEqual(data['exchange_rate'], '200.00000000')
        self.assertIn('payment_uri', data)

        self.assertEqual(prepare_mock.call_args[0][0], device)
        self.assertEqual(prepare_mock.call_args[0][1], Decimal('10'))

    @patch('api.views_v2_new.prepare_deposit')
    def test_create_from_terminal(self, prepare_mock):
        device = DeviceFactory(long_key=True)
        amount = 10
        bluetooth_mac = '12:34:56:78:9A:BC'
        prepare_mock.return_value = deposit = DepositFactory(
            account=device.account,
            device=device,
            amount=Decimal(amount),
            merchant_coin_amount=Decimal('0.0499'),
            fee_coin_amount=Decimal('0.0001'))

        url = reverse('api:v2:deposit-list')
        form_data = {
            'device': device.key,
            'amount': amount,
            'bt_mac': bluetooth_mac,
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['uid'], deposit.uid)
        self.assertEqual(data['fiat_amount'], '10.00')
        self.assertEqual(data['btc_amount'], '0.05000000')
        self.assertEqual(data['exchange_rate'], '200.00000000')
        self.assertIn('payment_uri', data)
        self.assertIn('payment_request', data)

    @patch('api.views_v2_new.prepare_deposit')
    def test_create_for_account(self, prepare_mock):
        account = AccountFactory()
        amount = 10
        prepare_mock.return_value = deposit = DepositFactory(
            account=account,
            device=None,
            amount=Decimal(amount),
            merchant_coin_amount=Decimal('0.0499'),
            fee_coin_amount=Decimal('0.0001'))

        url = reverse('api:v2:deposit-list')
        form_data = {
            'account': account.pk,
            'amount': amount,
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['uid'], deposit.uid)
        self.assertEqual(data['fiat_amount'], '10.00')
        self.assertEqual(data['btc_amount'], '0.05000000')
        self.assertEqual(data['exchange_rate'], '200.00000000')
        self.assertIn('payment_uri', data)
        self.assertEqual(prepare_mock.call_args[0][0], account)
        self.assertEqual(prepare_mock.call_args[0][1], Decimal('10'))

    def test_create_invalid_amount(self):
        device = DeviceFactory()
        url = reverse('api:v2:deposit-list')
        form_data = {
            'device': device.key,
            'amount': 'aaa',
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['amount'][0],
                         'A valid number is required.')

    def test_create_invalid_device_key(self):
        url = reverse('api:v2:deposit-list')
        form_data = {
            'device': 'invalidkey',
            'amount': '0.5',
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['device'][0],
                         'Invalid device key.')

    def test_create_not_active(self):
        device = DeviceFactory(status='activation_in_progress')
        url = reverse('api:v2:deposit-list')
        form_data = {
            'device': device.key,
            'amount': '0.5',
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['device'][0],
                         'Invalid device key.')

    @patch('api.views_v2_new.prepare_deposit')
    def test_payment_error(self, prepare_mock):
        prepare_mock.side_effect = PaymentError
        device = DeviceFactory(long_key=True)
        amount = 10
        bluetooth_mac = '12:34:56:78:9A:BC'
        url = reverse('api:v2:deposit-list')
        form_data = {
            'device': device.key,
            'amount': amount,
            'bt_mac': bluetooth_mac,
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['device'][0], 'Payment error')

import datetime
from decimal import Decimal
import hashlib

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone
from mock import patch, Mock
from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import status
from constance.test import override_config

from api.views_v2 import WithdrawalViewSet
from api.utils.crypto import create_test_signature, create_test_public_key
from operations import exceptions
from transactions.tests.factories import DepositFactory, WithdrawalFactory
from website.models import Device
from website.tests.factories import (
    AccountFactory,
    DeviceFactory,
    DeviceBatchFactory)


class DepositViewSetTestCase(APITestCase):

    @patch('api.views_v2.prepare_deposit')
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

    @patch('api.views_v2.prepare_deposit')
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

    @patch('api.views_v2.prepare_deposit')
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

    @patch('api.views_v2.prepare_deposit')
    def test_create_payment_error(self, prepare_mock):
        prepare_mock.side_effect = exceptions.PaymentError
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

    def test_retrieve_not_notified(self):
        deposit = DepositFactory()
        url = reverse('api:v2:deposit-detail',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['uid'], deposit.uid)
        self.assertEqual(data['status'], 'new')

    def test_retrieve_notified(self):
        deposit = DepositFactory(broadcasted=True)
        self.assertIsNone(deposit.time_notified)
        url = reverse('api:v2:deposit-detail',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data['uid'], deposit.uid)
        self.assertEqual(data['status'], 'notified')
        deposit.refresh_from_db()
        self.assertIsNotNone(deposit.time_notified)

    def test_cancel_new(self):
        deposit = DepositFactory()
        url = reverse('api:v2:deposit-cancel', kwargs={'uid': deposit.uid})
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        deposit.refresh_from_db()
        self.assertEqual(deposit.status, 'cancelled')

    def test_cancel_received(self):
        deposit = DepositFactory(received=True)
        url = reverse('api:v2:deposit-cancel', kwargs={'uid': deposit.uid})
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        deposit.refresh_from_db()
        self.assertEqual(deposit.status, 'cancelled')

    def test_cancel_broadcasted(self):
        deposit = DepositFactory(broadcasted=True)
        url = reverse('api:v2:deposit-cancel', kwargs={'uid': deposit.uid})
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('transactions.models.create_payment_request')
    def test_payment_request(self, create_mock):
        deposit = DepositFactory()
        create_mock.return_value = payment_request = '009A8B'.decode('hex')
        url = reverse('api:v2:deposit-payment-request',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'],
                         'application/bitcoin-paymentrequest')
        self.assertEqual(response.content, payment_request)

    def test_payment_request_timeout(self):
        deposit = DepositFactory(timeout=True)
        url = reverse('api:v2:deposit-payment-request',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_payment_request_cancelled(self):
        deposit = DepositFactory(cancelled=True)
        url = reverse('api:v2:deposit-payment-request',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.views_v2.handle_bip70_payment')
    def test_payment_response(self, parse_mock):
        deposit = DepositFactory()
        parse_mock.return_value = payment_ack = 'test'
        payment_response = '009A8B'.decode('hex')
        url = reverse('api:v2:deposit-payment-response',
                      kwargs={'uid': deposit.uid})
        response = self.client.post(
            url, payment_response,
            content_type='application/bitcoin-payment')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'],
                         'application/bitcoin-paymentack')
        self.assertEqual(response.content, payment_ack)

    def test_payment_response_invalid_headers(self):
        deposit = DepositFactory()
        payment_response = '009A8B'.decode('hex')
        url = reverse('api:v2:deposit-payment-response',
                      kwargs={'uid': deposit.uid})
        response = self.client.post(
            url, payment_response,
            content_type='application/octet-stream')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_payment_response_already_received(self):
        deposit = DepositFactory(received=True)
        url = reverse('api:v2:deposit-payment-response',
                      kwargs={'uid': deposit.uid})
        response = self.client.post(
            url, '',
            content_type='application/bitcoin-payment')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.utils.pdf.get_template')
    def test_receipt(self, get_template_mock):
        deposit = DepositFactory(notified=True)
        get_template_mock.return_value = template_mock = Mock(**{
            'render.return_value': 'test',
        })
        url = reverse('api:v2:deposit-receipt',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(get_template_mock.call_args[0][0],
                         'pdf/receipt_deposit.html')
        self.assertIs(template_mock.render.called, True)
        self.assertEqual(template_mock.render.call_args[0][0]['deposit'],
                         deposit)

    def test_receipt_not_notified(self):
        deposit = DepositFactory(broadcasted=True)
        url = reverse('api:v2:deposit-receipt',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.utils.pdf.get_template')
    def test_receipt_short(self, get_template_mock):
        deposit = DepositFactory(notified=True)
        get_template_mock.return_value = Mock(**{
            'render.return_value': 'test',
        })
        url = reverse('api:short:deposit-receipt',
                      kwargs={'uid': deposit.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_receipt_short_post(self):
        deposit = DepositFactory(notified=True)
        url = reverse('api:short:deposit-receipt',
                      kwargs={'uid': deposit.uid})
        response = self.client.post(url, {})
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)


class WithdrawalViewSetTestCase(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    @patch('api.views_v2.prepare_withdrawal')
    def test_create(self, prepare_mock):
        device = DeviceFactory.create()
        withdrawal = WithdrawalFactory(device=device, amount=Decimal('1.00'))
        prepare_mock.return_value = withdrawal

        view = WithdrawalViewSet.as_view(actions={'post': 'create'})
        form_data = {
            'device': device.key,
            'amount': '1.00',
        }
        url = reverse('api:v2:withdrawal-list')
        request = self.factory.post(url, form_data, format='multipart')
        device.api_key, request.META['HTTP_X_SIGNATURE'] = \
            create_test_signature(request.body)
        device.save()

        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uid'], withdrawal.uid)
        self.assertEqual(response.data['btc_amount'],
                         str(withdrawal.coin_amount))
        self.assertEqual(response.data['exchange_rate'],
                         str(withdrawal.effective_exchange_rate))
        self.assertEqual(response.data['status'], 'new')

    def test_create_invalid_device_key(self):
        form_data = {
            'device': 'invalid_key',
            'amount': '1.00',
        }
        url = reverse('api:v2:withdrawal-list')
        response = self.client.post(url, form_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['device'][0],
                         'Invalid device key.')

    def test_create_device_not_active(self):
        device = DeviceFactory.create(status='activation_in_progress')
        form_data = {
            'device': device.key,
            'amount': '1.00',
        }
        url = reverse('api:v2:withdrawal-list')
        response = self.client.post(url, form_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['device'][0],
                         'Invalid device key.')

    @patch('api.views_v2.prepare_withdrawal')
    def test_create_withdrawal_error(self, prepare_mock):
        device = DeviceFactory.create()
        prepare_mock.side_effect = exceptions.WithdrawalError(
            'Amount exceeds max payout for current device')
        view = WithdrawalViewSet.as_view(actions={'post': 'create'})
        data = {
            'device': device.key,
            'amount': '1.00',
        }
        url = reverse('api:v2:withdrawal-list')
        request = self.factory.post(url, data, format='multipart')
        device.api_key, request.META['HTTP_X_SIGNATURE'] = \
            create_test_signature(request.body)
        device.save()
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['device'][0],
                         'Amount exceeds max payout for current device')

    def test_create_invalid_signature(self):
        device = DeviceFactory.create()

        view = WithdrawalViewSet.as_view(actions={'post': 'create'})
        form_data = {
            'device': device.key,
            'amount': '1.00',
        }
        url = reverse('api:v2:withdrawal-list')
        request = self.factory.post(url, form_data, format='multipart')
        device.api_key, signature = create_test_signature(request.body)
        device.save()
        request.META['HTTP_X_SIGNATURE'] = 'invalid_sig'

        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('api.views_v2.send_transaction')
    def test_confirm(self, send_mock):
        def write_time_sent(withdrawal, address):
            withdrawal.time_sent = timezone.now()
            withdrawal.save()
        send_mock.side_effect = write_time_sent

        withdrawal = WithdrawalFactory()
        view = WithdrawalViewSet.as_view(actions={'post': 'confirm'})
        form_data = {'address': '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'}
        url = reverse('api:v2:withdrawal-confirm',
                      kwargs={'uid': withdrawal.uid})
        request = self.factory.post(url, form_data, format='multipart')
        withdrawal.device.api_key, request.META['HTTP_X_SIGNATURE'] = \
            create_test_signature(request.body)
        withdrawal.device.save()

        response = view(request, uid=withdrawal.uid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'sent')
        self.assertTrue(send_mock.called)

    def test_confirm_already_sent(self):
        withdrawal = WithdrawalFactory(sent=True)
        view = WithdrawalViewSet.as_view(actions={'post': 'confirm'})
        form_data = {'address': '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'}
        url = reverse('api:v2:withdrawal-confirm',
                      kwargs={'uid': withdrawal.uid})
        request = self.factory.post(url, form_data, format='multipart')
        withdrawal.device.api_key, request.META['HTTP_X_SIGNATURE'] = \
            create_test_signature(request.body)
        withdrawal.device.save()

        response = view(request, uid=withdrawal.uid)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel(self):
        withdrawal = WithdrawalFactory.create()
        view = WithdrawalViewSet.as_view(actions={'post': 'cancel'})
        url = reverse('api:v2:withdrawal-cancel',
                      kwargs={'uid': withdrawal.uid})
        request = self.factory.post(url, {}, format='multipart')
        withdrawal.device.api_key, request.META['HTTP_X_SIGNATURE'] = \
            create_test_signature(request.body)
        withdrawal.device.save()

        response = view(request, uid=withdrawal.uid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'cancelled')

    def test_cancel_not_new(self):
        withdrawal = WithdrawalFactory(sent=True)
        view = WithdrawalViewSet.as_view(actions={'post': 'cancel'})
        url = reverse('api:v2:withdrawal-cancel',
                      kwargs={'uid': withdrawal.uid})
        request = self.factory.post(url, {}, format='multipart')
        withdrawal.device.api_key, request.META['HTTP_X_SIGNATURE'] = \
            create_test_signature(request.body)
        withdrawal.device.save()

        response = view(request, uid=withdrawal.uid)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve(self):
        withdrawal = WithdrawalFactory(sent=True)
        url = reverse('api:v2:withdrawal-detail',
                      kwargs={'uid': withdrawal.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'sent')

        withdrawal.time_broadcasted = timezone.now()
        withdrawal.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'notified')

    @patch('api.utils.pdf.get_template')
    def test_receipt(self, get_template_mock):
        get_template_mock.return_value = template_mock = Mock(**{
            'render.return_value': 'test',
        })
        withdrawal = WithdrawalFactory(notified=True)
        url = reverse('api:v2:withdrawal-receipt',
                      kwargs={'uid': withdrawal.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(get_template_mock.call_args[0][0],
                         'pdf/receipt_withdrawal.html')
        self.assertIs(template_mock.render.called, True)
        self.assertEqual(template_mock.render.call_args[0][0]['withdrawal'],
                         withdrawal)

    def test_receipt_not_notified(self):
        withdrawal = WithdrawalFactory(broadcasted=True)
        url = reverse('api:v2:withdrawal-receipt',
                      kwargs={'uid': withdrawal.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.utils.pdf.get_template')
    def test_receipt_short(self, get_template_mock):
        get_template_mock.return_value = Mock(**{
            'render.return_value': 'test',
        })
        withdrawal = WithdrawalFactory(notified=True)
        url = reverse('api:short:withdrawal-receipt',
                      kwargs={'uid': withdrawal.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_receipt_short_post(self):
        withdrawal = WithdrawalFactory(notified=True)
        url = reverse('api:short:withdrawal-receipt',
                      kwargs={'uid': withdrawal.uid})
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
        self.assertEqual(response.data['batch'][0],
                         'This field is required.')
        self.assertEqual(response.data['key'][0],
                         'This field is required.')
        self.assertEqual(response.data['api_key'][0],
                         'This field is required.')

    @patch('api.views_v2.rq_helpers.run_task')
    def test_retrieve_registered(self, run_mock):
        device = DeviceFactory.create(status='registered')
        url = reverse('api:v2:device-detail',
                      kwargs={'key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'registered')
        self.assertEqual(response.data['language']['code'], 'en')
        self.assertEqual(response.data['currency']['name'], 'GBP')

    @patch('api.views_v2.rq_helpers.run_task')
    def test_retrieve_activation(self, run_mock):
        device = DeviceFactory.create(status='activation_in_progress')
        url = reverse('api:v2:device-detail',
                      kwargs={'key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'activation_in_progress')

    @patch('api.views_v2.rq_helpers.run_task')
    def test_retrieve_active(self, run_mock):
        device = DeviceFactory.create(status='active')
        url = reverse('api:v2:device-detail',
                      kwargs={'key': device.key})
        self.assertFalse(device.is_online())
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'active')

        updated_device = Device.objects.get(pk=device.pk)
        self.assertTrue(updated_device.is_online())

        self.assertIs(run_mock.called, True)
        self.assertEqual(run_mock.call_args[0][1][0], device.key)
        self.assertEqual(run_mock.call_args[1]['time_delta'],
                         datetime.timedelta(minutes=3))

    @override_config(ENABLE_SALT=False)
    @patch('api.views_v2.rq_helpers.run_task')
    def test_retrieve_active_salt_disabled(self, run_mock):
        device = DeviceFactory.create(status='active')
        url = reverse('api:v2:device-detail',
                      kwargs={'key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIs(run_mock.called, False)

    @patch('api.views_v2.rq_helpers.run_task')
    def test_retrieve_suspended(self, run_mock):
        device = DeviceFactory.create(status='suspended')
        url = reverse('api:v2:device-detail',
                      kwargs={'key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_confirm_activation(self):
        device = DeviceFactory.create(status='activation_in_progress')
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


class PingViewTestCase(APITestCase):

    def test_ping(self):
        url = reverse('api:v2:ping')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'online')

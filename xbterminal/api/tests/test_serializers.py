# -*- coding: utf-8 -*-

from decimal import Decimal
import hashlib
from mock import Mock, patch
from django.test import TestCase

from operations.tests.factories import WithdrawalOrderFactory
from website.models import Language, Currency
from website.tests.factories import (
    AccountFactory,
    DeviceBatchFactory,
    DeviceFactory)
from api.serializers import (
    PaymentInitSerializer,
    WithdrawalOrderSerializer,
    DeviceSerializer,
    DeviceRegistrationSerializer)
from api.utils import activation
from api.utils.crypto import create_test_public_key


class PaymentInitSerializerTestCase(TestCase):

    def test_validate_with_device(self):
        device = DeviceFactory.create(status='active')
        data = {
            'device': device.key,
            'amount': '1.25',
        }
        serializer = PaymentInitSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['device'].pk,
                         device.pk)
        self.assertEqual(serializer.validated_data['amount'],
                         Decimal('1.25'))
        self.assertIsNone(serializer.validated_data.get('bt_mac'))

    def test_validate_with_account(self):
        account = AccountFactory.create()
        data = {
            'account': account.pk,
            'amount': '1.25',
        }
        serializer = PaymentInitSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['account'].pk,
                         account.pk)

    def test_no_device_no_account(self):
        data = {
            'amount': '1.25',
        }
        serializer = PaymentInitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.error_message,
                         'Either device or account must be specified.')

    def test_invalid_device_key(self):
        data = {
            'device': '120313',
            'amount': '1.25',
        }
        serializer = PaymentInitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.error_message,
                         'Device - invalid device key.')

    def test_invalid_bt_mac(self):
        device = DeviceFactory.create(status='active')
        data = {
            'device': device.key,
            'amount': '1.25',
            'bt_mac': '00:11:22:33:44'
        }
        serializer = PaymentInitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.error_message,
                         'Bt_mac - this value does not match the required pattern.')


class WithdrawalOrderSerializerTestCase(TestCase):

    def test_serialization(self):
        order = WithdrawalOrderFactory.create()
        data = WithdrawalOrderSerializer(order).data
        self.assertEqual(data['uid'], order.uid)
        self.assertEqual(data['fiat_amount'], str(order.fiat_amount))
        self.assertEqual(data['btc_amount'], str(order.btc_amount))
        self.assertEqual(data['exchange_rate'],
                         str(order.effective_exchange_rate))
        self.assertEqual(data['status'], order.status)


class DeviceSerializerTestCase(TestCase):

    def test_registered(self):
        device = DeviceFactory.create(status='registered')
        data = DeviceSerializer(device).data
        self.assertEqual(data['status'], 'registered')
        self.assertEqual(data['bitcoin_network'], 'mainnet')
        self.assertEqual(data['language']['code'], 'en')
        self.assertEqual(data['currency']['name'], 'GBP')

    def test_activation(self):
        device = DeviceFactory.create(status='activation')
        data = DeviceSerializer(device).data
        self.assertEqual(data['status'], 'activation_in_progress')
        activation.set_status(device, 'error')
        data = DeviceSerializer(device).data
        self.assertEqual(data['status'], 'activation_error')

    def test_operational(self):
        device = DeviceFactory.create(
            merchant__language=Language.objects.get(code='de'),
            merchant__currency=Currency.objects.get(name='EUR'))
        data = DeviceSerializer(device).data
        self.assertEqual(data['status'], 'active')
        self.assertEqual(data['bitcoin_network'], 'mainnet')
        self.assertEqual(data['language']['code'], 'de')
        self.assertEqual(data['language']['fractional_split'], '.')
        self.assertEqual(data['language']['thousands_split'], ',')
        self.assertEqual(data['currency']['name'], 'EUR')
        self.assertEqual(data['currency']['prefix'], u'€')


class DeviceRegistrationSerializerTestCase(TestCase):

    @patch('api.serializers.Salt')
    def test_validation(self, salt_cls_mock):
        salt_cls_mock.return_value = salt_mock = Mock(**{
            'check_fingerprint.return_value': True})
        batch = DeviceBatchFactory.create()
        device_key = hashlib.sha256('test').hexdigest()
        api_key = create_test_public_key()
        data = {
            'batch': batch.batch_number,
            'key': device_key,
            'api_key': api_key,
            'salt_fingerprint': 'fingerprint',
        }
        serializer = DeviceRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertTrue(salt_mock.login.called)
        self.assertTrue(salt_mock.check_fingerprint.called)
        device = serializer.save()
        self.assertFalse(salt_mock.accept.called)
        self.assertEqual(device.device_type, 'hardware')
        self.assertIsNone(device.merchant)
        self.assertIsNone(device.account)
        self.assertEqual(device.status, 'registered')
        self.assertEqual(device.key, device_key)
        self.assertEqual(device.api_key, api_key)
        self.assertEqual(device.batch.pk, batch.pk)

    @patch('api.serializers.Salt')
    def test_batch_size(self, salt_cls_mock):
        salt_cls_mock.return_value = Mock(**{
            'check_fingerprint.return_value': True})
        batch = DeviceBatchFactory.create(size=0)
        data = {
            'batch': batch.batch_number,
            'key': '0' * 64,
            'api_key': create_test_public_key(),
            'salt_fingerprint': 'fingerprint',
        }
        serializer = DeviceRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['batch'][0],
                         'Registration limit exceeded.')

    @patch('api.serializers.Salt')
    def test_invalid_device_key(self, salt_cls_mock):
        salt_cls_mock.return_value = Mock(**{
            'check_fingerprint.return_value': True})
        batch = DeviceBatchFactory.create()
        data = {
            'batch': batch.batch_number,
            'api_key': create_test_public_key(),
            'salt_fingerprint': 'fingerprint',
        }
        serializer = DeviceRegistrationSerializer(data=data.copy())
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['key'][0],
                         'This field is required.')

        data['key'] = 'X813EV'
        serializer = DeviceRegistrationSerializer(data=data.copy())
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['key'][0],
                         'Invalid device key.')

        device = DeviceFactory.create(
            key=hashlib.sha256('test').hexdigest())
        data['key'] = device.key
        serializer = DeviceRegistrationSerializer(data=data.copy())
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['key'][0],
                         'Device is already registered.')

    @patch('api.serializers.Salt')
    def test_invalid_api_key(self, salt_cls_mock):
        salt_cls_mock.return_value = Mock(**{
            'check_fingerprint.return_value': True})
        batch = DeviceBatchFactory.create()
        data = {
            'batch': batch.batch_number,
            'key': '0' * 64,
            'salt_fingerprint': 'fingerprint',
        }
        serializer = DeviceRegistrationSerializer(data=data.copy())
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['api_key'][0],
                         'This field is required.')

        data['api_key'] = 'invalid api key'
        serializer = DeviceRegistrationSerializer(data=data.copy())
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['api_key'][0],
                         'Invalid API public key.')

    @patch('api.serializers.Salt')
    def test_invalid_salt_fingerprint(self, salt_cls_mock):
        salt_cls_mock.return_value = salt_mock = Mock(**{
            'check_fingerprint.return_value': False,
        })
        batch = DeviceBatchFactory.create()
        device_key = hashlib.sha256('test').hexdigest()
        api_key = create_test_public_key()
        data = {
            'batch': batch.batch_number,
            'key': device_key,
            'api_key': api_key,
        }
        serializer = DeviceRegistrationSerializer(data=data.copy())
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['salt_fingerprint'][0],
                         'This field is required.')

        data['salt_fingerprint'] = 'fingerprint'
        serializer = DeviceRegistrationSerializer(data=data.copy())
        self.assertFalse(serializer.is_valid())
        self.assertTrue(salt_mock.check_fingerprint.called)
        self.assertEqual(serializer.errors['salt_fingerprint'][0],
                         'Invalid salt key fingerprint.')

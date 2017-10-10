# -*- coding: utf-8 -*-

from decimal import Decimal
import hashlib
from mock import Mock, patch
from django.test import TestCase

from transactions.tests.factories import DepositFactory, WithdrawalFactory
from website.models import Language, Currency
from website.tests.factories import (
    MerchantAccountFactory,
    AccountFactory,
    DeviceBatchFactory,
    DeviceFactory)
from api.serializers import (
    MerchantSerializer,
    PaymentInitSerializer,
    DepositSerializer,
    WithdrawalInitSerializer,
    WithdrawalSerializer,
    DeviceSerializer,
    DeviceRegistrationSerializer)
from api.utils.crypto import create_test_public_key


class MerchantSerializerTestCase(TestCase):

    def test_serialization(self):
        merchant = MerchantAccountFactory.create()
        data = MerchantSerializer(merchant).data
        self.assertEqual(data['id'], merchant.pk)
        self.assertEqual(data['company_name'], merchant.company_name)
        self.assertEqual(data['contact_first_name'],
                         merchant.contact_first_name)
        self.assertEqual(data['contact_last_name'],
                         merchant.contact_last_name)
        self.assertEqual(data['contact_email'], merchant.contact_email)
        self.assertEqual(data['verification_status'],
                         merchant.verification_status)


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
        self.assertEqual(serializer.errors['non_field_errors'][0],
                         'Either device or account must be specified.')

    def test_invalid_device_key(self):
        data = {
            'device': '120313',
            'amount': '1.25',
        }
        serializer = PaymentInitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['device'][0],
                         'Invalid device key.')

    def test_invalid_bt_mac(self):
        device = DeviceFactory.create(status='active')
        data = {
            'device': device.key,
            'amount': '1.25',
            'bt_mac': '00:11:22:33:44'
        }
        serializer = PaymentInitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['bt_mac'][0],
                         'This value does not match the required pattern.')


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


class WithdrawalInitSerializerTestCase(TestCase):

    def test_validation(self):
        device = DeviceFactory.create()
        data = {
            'device': device.key,
            'amount': '0.50',
        }
        serializer = WithdrawalInitSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['device'].pk,
                         device.pk)
        self.assertEqual(serializer.validated_data['amount'],
                         Decimal('0.5'))

    def test_invalid_device_key(self):
        data = {
            'device': 'invalidkey',
            'amount': '0.50',
        }
        serializer = WithdrawalInitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['device'][0],
                         'Invalid device key.')

    def test_invalid_amount(self):
        device = DeviceFactory.create()
        data = {
            'device': device.key,
            'amount': '0.00',
        }
        serializer = WithdrawalInitSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['amount'][0],
            'Ensure this value is greater than or equal to 0.01.')


class WithdrawalSerializerTestCase(TestCase):

    def test_serialization(self):
        withdrawal = WithdrawalFactory()
        data = WithdrawalSerializer(withdrawal).data
        self.assertEqual(data['uid'], withdrawal.uid)
        self.assertEqual(data['fiat_amount'].rstrip('0'),
                         str(withdrawal.amount).rstrip('0'))
        self.assertEqual(data['btc_amount'], str(withdrawal.coin_amount))
        self.assertEqual(data['tx_fee_btc_amount'].rstrip('0'),
                         str(withdrawal.tx_fee_coin_amount))
        self.assertEqual(data['exchange_rate'],
                         str(withdrawal.effective_exchange_rate))
        self.assertEqual(data['address'], withdrawal.customer_address)
        self.assertEqual(data['status'], withdrawal.status)


class DeviceSerializerTestCase(TestCase):

    def test_registered(self):
        device = DeviceFactory.create(status='registered')
        data = DeviceSerializer(device).data
        self.assertEqual(data['status'], 'registered')
        self.assertIsNone(data['coin'])
        self.assertEqual(data['bitcoin_network'], 'mainnet')
        self.assertEqual(data['language']['code'], 'en')
        self.assertEqual(data['currency']['name'], 'GBP')
        self.assertIsNone(data['settings']['amount_1'])
        self.assertIsNone(data['settings']['amount_2'])
        self.assertIsNone(data['settings']['amount_3'])
        self.assertIsNone(data['settings']['amount_shift'])

    def test_activation(self):
        device = DeviceFactory.create(status='activation_in_progress')
        data = DeviceSerializer(device).data
        self.assertEqual(data['status'], 'activation_in_progress')
        device.set_activation_error()
        device.save()
        data = DeviceSerializer(device).data
        self.assertEqual(data['status'], 'activation_error')

    def test_operational_btc(self):
        device = DeviceFactory.create(
            merchant__language=Language.objects.get(code='de'),
            merchant__currency=Currency.objects.get(name='EUR'))
        data = DeviceSerializer(device).data
        self.assertEqual(data['status'], 'active')
        self.assertEqual(data['coin'], 'BTC')
        self.assertEqual(data['bitcoin_network'], 'mainnet')
        self.assertEqual(data['language']['code'], 'de')
        self.assertEqual(data['language']['fractional_split'], '.')
        self.assertEqual(data['language']['thousands_split'], ',')
        self.assertEqual(data['currency']['name'], 'EUR')
        self.assertEqual(data['currency']['prefix'], u'€')
        self.assertEqual(data['settings']['amount_1'],
                         str(device.amount_1))
        self.assertEqual(data['settings']['amount_2'],
                         str(device.amount_2))
        self.assertEqual(data['settings']['amount_3'],
                         str(device.amount_3))
        self.assertEqual(data['settings']['amount_shift'],
                         str(device.amount_shift))

    def test_operational_dash(self):
        device = DeviceFactory(account__currency__name='DASH')
        data = DeviceSerializer(device).data
        self.assertEqual(data['coin'], 'DASH')
        self.assertEqual(data['bitcoin_network'], 'mainnet')


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

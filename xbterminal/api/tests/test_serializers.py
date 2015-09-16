# -*- coding: utf-8 -*-

import hashlib
from django.test import TestCase

from operations.tests.factories import WithdrawalOrderFactory
from website.models import Language, Currency
from website.tests.factories import (
    DeviceBatchFactory,
    DeviceFactory)
from api.serializers import (
    WithdrawalOrderSerializer,
    DeviceSerializer,
    DeviceRegistrationSerializer)
from api.utils import create_test_public_key


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

    def test_activation(self):
        device = DeviceFactory.create(status='activation')
        data = DeviceSerializer(device).data
        self.assertEqual(data['status'], 'activation')
        self.assertEqual(data['bitcoin_network'], 'mainnet')
        self.assertEqual(data['language']['code'], 'en')
        self.assertEqual(data['currency']['name'], 'GBP')

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

    def test_validation(self):
        batch = DeviceBatchFactory.create()
        device_key = hashlib.sha256('test').hexdigest()
        api_key = create_test_public_key()
        data = {
            'batch': batch.batch_number,
            'key': device_key,
            'api_key': api_key,
        }
        serializer = DeviceRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        device = serializer.save()
        self.assertEqual(device.device_type, 'hardware')
        self.assertIsNone(device.merchant)
        self.assertEqual(device.status, 'activation')
        self.assertEqual(device.key, device_key)
        self.assertEqual(device.api_key, api_key)
        self.assertEqual(device.batch.pk, batch.pk)

    def test_batch_size(self):
        batch = DeviceBatchFactory.create(size=0)
        data = {
            'batch': batch.batch_number,
            'key': '0' * 64,
            'api_key': create_test_public_key(),
        }
        serializer = DeviceRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['batch'][0],
                         'Registration limit exceeded.')

    def test_invalid_device_key(self):
        batch = DeviceBatchFactory.create()
        data = {
            'batch': batch.batch_number,
            'api_key': create_test_public_key(),
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

    def test_invalid_api_key(self):
        batch = DeviceBatchFactory.create()
        data = {
            'batch': batch.batch_number,
            'key': '0' * 64,
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

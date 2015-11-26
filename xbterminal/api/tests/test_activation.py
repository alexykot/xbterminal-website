from mock import Mock, patch
from django.test import TestCase

from api.utils.activation import prepare_device
from website.models import Device
from website.tests.factories import DeviceFactory


class ActivationTestCase(TestCase):

    @patch('api.utils.activation.Salt')
    def test_prepare_device(self, salt_cls_mock):
        salt_cls_mock.return_value = salt_mock = Mock(**{
            'ping.return_value': True,
        })
        device = DeviceFactory.create(status='activation')

        prepare_device(device.key)
        self.assertTrue(salt_mock.accept.called)
        self.assertTrue(salt_mock.ping.called)

        device_updated = Device.objects.get(key=device.key)
        self.assertEqual(device_updated.status, 'active')

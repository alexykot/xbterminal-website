from mock import Mock, patch
from django.test import TestCase

from api.utils.activation import prepare_device, get_status
from website.models import Device
from website.tests.factories import DeviceFactory


class ActivationTestCase(TestCase):

    @patch('api.utils.activation.Salt')
    @patch('api.utils.activation.get_latest_xbtfw_version')
    def test_prepare_device(self, get_version_mock, salt_cls_mock):
        salt_cls_mock.return_value = salt_mock = Mock(**{
            'ping.return_value': True,
        })
        get_version_mock.return_value = '1.0'
        device = DeviceFactory.create(status='activation')

        prepare_device(device.key)
        self.assertTrue(salt_mock.accept.called)
        self.assertTrue(salt_mock.ping.called)
        self.assertTrue(salt_mock.upgrade.called)
        self.assertEqual(salt_mock.upgrade.call_args[0][1], '1.0')
        self.assertTrue(salt_mock.reboot.called)

        device_updated = Device.objects.get(key=device.key)
        self.assertEqual(device_updated.status, 'active')

    def test_get_status(self):
        device = DeviceFactory.create(status='activation')
        status = get_status(device)
        self.assertEqual(status, 'in progress')

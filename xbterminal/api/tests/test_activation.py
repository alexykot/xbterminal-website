from mock import Mock, patch
from django.test import TestCase

from api.utils.activation import (
    prepare_device,
    get_status,
    set_status,
    wait_for_activation)
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

    def test_get_status_default(self):
        device = DeviceFactory.create(status='activation')
        status = get_status(device)
        self.assertEqual(status, 'in_progress')

    def test_get_status_error(self):
        device = DeviceFactory.create(status='activation')
        with self.assertRaises(AssertionError):
            set_status(device, 'test')
        set_status(device, 'error')
        status = get_status(device)
        self.assertEqual(status, 'error')

    @patch('api.utils.activation.Job.fetch')
    @patch('api.utils.activation.rq_helpers.cancel_current_task')
    def test_wait_for_activation(self, cancel_mock, job_fetch_mock):
        job_fetch_mock.return_value = Mock(is_failed=False)
        device = DeviceFactory.create(status='activation')
        job_id = 'test'
        wait_for_activation(device.key, job_id)
        self.assertFalse(cancel_mock.called)

    @patch('api.utils.activation.rq_helpers.cancel_current_task')
    def test_wait_for_activation_finished(self, cancel_mock):
        device = DeviceFactory.create(status='active')
        job_id = 'test'
        wait_for_activation(device.key, job_id)
        self.assertTrue(cancel_mock.called)

    @patch('api.utils.activation.Job.fetch')
    @patch('api.utils.activation.rq_helpers.cancel_current_task')
    def test_wait_for_activation_error(self, cancel_mock, job_fetch_mock):
        job_fetch_mock.return_value = Mock(is_failed=True)
        device = DeviceFactory.create(status='activation')
        job_id = 'test'
        wait_for_activation(device.key, job_id)
        self.assertTrue(cancel_mock.called)
        status = get_status(device)
        self.assertEqual(status, 'error')

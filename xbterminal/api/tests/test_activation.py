import datetime
from mock import Mock, patch
from django.test import TestCase
from django.utils import timezone

from api.utils.activation import (
    start,
    prepare_device,
    get_status,
    set_status,
    wait_for_activation)
from website.models import Device
from website.tests.factories import (
    MerchantAccountFactory,
    AccountFactory,
    DeviceFactory)


class ActivationTestCase(TestCase):

    @patch('api.utils.activation.rq_helpers.run_task')
    @patch('api.utils.activation.rq_helpers.run_periodic_task')
    def test_start(self, run_periodic_mock, run_mock):
        merchant = MerchantAccountFactory.create(currency__name='USD')
        AccountFactory.create(merchant=merchant, currency__name='BTC')
        AccountFactory.create(merchant=merchant, currency__name='GBP')
        account_usd = AccountFactory.create(merchant=merchant,
                                            currency__name='USD')
        device = DeviceFactory.create(status='registered')
        start(device, merchant)
        self.assertTrue(run_mock.called)
        self.assertEqual(run_mock.call_args[1]['timeout'], 1500)
        self.assertTrue(run_periodic_mock.called)
        device_updated = Device.objects.get(pk=device.pk)
        self.assertEqual(device_updated.status, 'activation')
        self.assertEqual(device_updated.merchant.pk, merchant.pk)
        self.assertEqual(device_updated.account.pk, account_usd.pk)

    @patch('api.utils.activation.rq_helpers.run_task')
    @patch('api.utils.activation.rq_helpers.run_periodic_task')
    def test_start_with_activation(self, run_periodic_mock, run_mock):

        def activate(fun, args, queue=None, timeout=None):
            device = Device.objects.get(key=args[0])
            device.activate()
            device.save()
            return Mock()
        run_mock.side_effect = activate

        merchant = MerchantAccountFactory.create(currency__name='USD')
        account = AccountFactory.create(merchant=merchant,
                                        currency__name='BTC')
        device = DeviceFactory.create(status='registered')

        start(device, merchant)
        device_updated = Device.objects.get(pk=device.pk)
        self.assertEqual(device_updated.status, 'active')
        self.assertEqual(device_updated.merchant.pk, merchant.pk)
        self.assertEqual(device_updated.account.pk, account.pk)

    @patch('api.utils.activation.Salt')
    @patch('api.utils.activation.get_latest_version')
    def test_prepare_device(self, get_version_mock, salt_cls_mock):
        salt_cls_mock.return_value = salt_mock = Mock(**{
            'ping.return_value': True,
            'get_grain.return_value': 'qemuarm',
        })
        get_version_mock.side_effect = ['1.0', '1.0-theme']
        device = DeviceFactory.create(status='activation')

        prepare_device(device.key)
        self.assertTrue(salt_mock.accept.called)
        self.assertTrue(salt_mock.ping.called)
        self.assertTrue(salt_mock.get_grain.called)
        self.assertEqual(get_version_mock.call_count, 2)
        self.assertEqual(get_version_mock.call_args[0][0], 'qemuarm')

        self.assertTrue(salt_mock.highstate.called)
        self.assertEqual(salt_mock.highstate.call_args[0][0], device.key)
        self.assertEqual(salt_mock.highstate.call_args[0][2], 1200)
        pillar_data = salt_mock.highstate.call_args[0][1]
        self.assertEqual(pillar_data['xbt']['version'], '1.0')
        self.assertEqual(pillar_data['xbt']['themes']['default'], '1.0-theme')
        self.assertEqual(pillar_data['xbt']['config']['theme'], 'default')

        self.assertFalse(salt_mock.reboot.called)

        device_updated = Device.objects.get(key=device.key)
        self.assertEqual(device_updated.status, 'activation')  # Not changed

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
        job_fetch_mock.return_value = Mock(
            is_failed=False,
            started_at=timezone.now(),
            timeout=600)
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
    def test_wait_for_activation_timeout(self, cancel_mock, job_fetch_mock):
        job_fetch_mock.return_value = Mock(
            started_at=timezone.now() - datetime.timedelta(minutes=20),
            timeout=600)
        device = DeviceFactory.create(status='activation')
        job_id = 'test'
        wait_for_activation(device.key, job_id)
        self.assertTrue(cancel_mock.called)
        status = get_status(device)
        self.assertEqual(status, 'error')

    @patch('api.utils.activation.Job.fetch')
    @patch('api.utils.activation.rq_helpers.cancel_current_task')
    def test_wait_for_activation_error(self, cancel_mock, job_fetch_mock):
        job_fetch_mock.return_value = Mock(
            is_failed=True,
            started_at=timezone.now(),
            timeout=600)
        device = DeviceFactory.create(status='activation')
        job_id = 'test'
        wait_for_activation(device.key, job_id)
        self.assertTrue(cancel_mock.called)
        status = get_status(device)
        self.assertEqual(status, 'error')

import datetime
from mock import Mock, patch

from django.test import TestCase

from django_fsm import TransitionNotAllowed
from rq.job import NoSuchJobError

from api.utils.activation import (
    start,
    prepare_device,
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
        account_gbp = AccountFactory(merchant=merchant,  # noqa: F841
                                     currency__name='GBP')
        account_usd = AccountFactory(merchant=merchant,  # noqa: F841
                                     currency__name='USD')
        account_btc = AccountFactory(merchant=merchant,
                                     currency__name='BTC')
        account_tbtc = AccountFactory(merchant=merchant,  # noqa: F841
                                      currency__name='TBTC')
        device = DeviceFactory.create(status='registered')
        start(device, merchant)
        self.assertTrue(run_mock.called)
        self.assertEqual(run_mock.call_args[1]['timeout'], 2400)
        self.assertTrue(run_periodic_mock.called)
        device_updated = Device.objects.get(pk=device.pk)
        self.assertEqual(device_updated.status, 'activation_in_progress')
        self.assertEqual(device_updated.merchant.pk, merchant.pk)
        self.assertEqual(device_updated.account.pk, account_btc.pk)
        self.assertEqual(device.amount_1,
                         merchant.currency.amount_1)
        self.assertEqual(device.amount_2,
                         merchant.currency.amount_2)
        self.assertEqual(device.amount_3,
                         merchant.currency.amount_3)
        self.assertEqual(device.amount_shift,
                         merchant.currency.amount_shift)
        self.assertEqual(device.max_payout,
                         account_btc.currency.max_payout)

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

    def test_start_no_account(self):
        merchant = MerchantAccountFactory.create(currency__name='GBP')
        AccountFactory(merchant=merchant, currency__name='GBP')
        device = DeviceFactory.create(status='registered')
        with self.assertRaises(TransitionNotAllowed):
            start(device, merchant)

    @patch('api.utils.activation.Salt')
    @patch('api.utils.activation.get_latest_version')
    def test_prepare_device(self, get_version_mock, salt_cls_mock):
        salt_cls_mock.return_value = salt_mock = Mock(**{
            'ping.return_value': True,
            'get_grain.return_value': 'qemuarm',
        })
        get_version_mock.side_effect = ['1.0', '1.1', '1.1-theme']
        device = DeviceFactory.create(status='activation_in_progress')

        prepare_device(device.key)
        self.assertTrue(salt_mock.accept.called)
        self.assertTrue(salt_mock.ping.called)
        self.assertEqual(salt_mock.get_grain.call_count, 1)
        self.assertEqual(get_version_mock.call_count, 3)
        self.assertEqual(get_version_mock.call_args_list[0][0][0],
                         'qemuarm')
        self.assertEqual(get_version_mock.call_args_list[0][0][1],
                         'xbterminal-rpc')
        self.assertEqual(get_version_mock.call_args_list[1][0][1],
                         'xbterminal-gui')
        self.assertEqual(get_version_mock.call_args_list[2][0][1],
                         'xbterminal-gui-theme-default')

        self.assertTrue(salt_mock.highstate.called)
        self.assertEqual(salt_mock.highstate.call_args[0][0], device.key)
        self.assertEqual(salt_mock.highstate.call_args[0][2], 1800)
        pillar_data = salt_mock.highstate.call_args[0][1]
        self.assertEqual(pillar_data['xbt']['rpc_version'], '1.0')
        self.assertEqual(pillar_data['xbt']['gui_version'], '1.1')
        self.assertEqual(pillar_data['xbt']['themes']['default'], '1.1-theme')
        self.assertEqual(pillar_data['xbt']['rpc_config'], {})
        self.assertEqual(pillar_data['xbt']['gui_config']['theme'], 'default')

        self.assertFalse(salt_mock.reboot.called)

        device_updated = Device.objects.get(key=device.key)
        self.assertEqual(device_updated.status,
                         'activation_in_progress')  # Not changed

    @patch('api.utils.activation.Job.fetch')
    @patch('api.utils.activation.rq_helpers.cancel_current_task')
    def test_wait_for_activation(self, cancel_mock, job_fetch_mock):
        job_fetch_mock.return_value = Mock(
            is_failed=False,
            started_at=datetime.datetime.now(),
            timeout=600)
        device = DeviceFactory.create(status='activation_in_progress')
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
    def test_wait_for_activation_no_such_job(self, cancel_mock, job_fetch_mock):
        job_fetch_mock.side_effect = NoSuchJobError
        device = DeviceFactory.create(status='activation_in_progress')
        job_id = 'test'
        wait_for_activation(device.key, job_id)
        self.assertFalse(cancel_mock.called)

    @patch('api.utils.activation.Job.fetch')
    @patch('api.utils.activation.rq_helpers.cancel_current_task')
    def test_wait_for_activation_timeout(self, cancel_mock, job_fetch_mock):
        job_fetch_mock.return_value = Mock(
            started_at=datetime.datetime.now() - datetime.timedelta(minutes=20),
            timeout=600)
        device = DeviceFactory.create(status='activation_in_progress')
        job_id = 'test'
        wait_for_activation(device.key, job_id)
        self.assertTrue(cancel_mock.called)
        device_updated = Device.objects.get(pk=device.pk)
        self.assertEqual(device_updated.status, 'activation_error')

    @patch('api.utils.activation.Job.fetch')
    @patch('api.utils.activation.rq_helpers.cancel_current_task')
    def test_wait_for_activation_error(self, cancel_mock, job_fetch_mock):
        job_fetch_mock.return_value = Mock(
            is_failed=True,
            started_at=datetime.datetime.now(),
            timeout=600)
        device = DeviceFactory.create(status='activation_in_progress')
        job_id = 'test'
        wait_for_activation(device.key, job_id)
        self.assertTrue(cancel_mock.called)
        device_updated = Device.objects.get(pk=device.pk)
        self.assertEqual(device_updated.status, 'activation_error')

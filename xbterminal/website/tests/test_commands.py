import datetime
from decimal import Decimal

from django.test import TestCase
from django.core import mail
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone
from mock import patch, Mock

from website.models import Device, INSTANTFIAT_PROVIDERS
from website.tests.factories import (
    MerchantAccountFactory,
    AccountFactory,
    DeviceFactory,
    ReconciliationTimeFactory)
from website.management.commands.check_wallet import \
    check_wallet, check_wallet_strict
from website.management.commands.withdraw_btc import withdraw_btc
from website.management.commands.cryptopay_sync import cryptopay_sync
from operations.tests.factories import outpoint_factory


class SendReconciliationTestCase(TestCase):

    def test_rectime_not_added(self):
        device = DeviceFactory.create()
        device.last_reconciliation = \
            timezone.now() - datetime.timedelta(days=1)
        device.save()
        call_command('send_reconciliation')
        self.assertEqual(len(mail.outbox), 0)
        device_updated = Device.objects.get(pk=device.pk)
        self.assertEqual(device_updated.last_reconciliation,
                         device.last_reconciliation)

    def test_not_ready(self):
        device = DeviceFactory.create()
        ReconciliationTimeFactory.create(
            device=device, time=datetime.time(0, 0))
        call_command('send_reconciliation')
        self.assertEqual(len(mail.outbox), 0)
        device_updated = Device.objects.get(pk=device.pk)
        self.assertEqual(device_updated.last_reconciliation,
                         device.last_reconciliation)

    def test_send(self):
        device = DeviceFactory.create()
        device.last_reconciliation = \
            timezone.now() - datetime.timedelta(days=1)
        device.save()
        rectime = ReconciliationTimeFactory.create(
            device=device, time=datetime.time(0, 0))
        call_command('send_reconciliation')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], rectime.email)
        device_updated = Device.objects.get(pk=device.pk)
        self.assertGreater(device_updated.last_reconciliation,
                           device.last_reconciliation)


class CheckWalletTestCase(TestCase):

    @patch('website.management.commands.check_wallet.BlockChain')
    @patch('website.utils.email.send_balance_admin_notification')
    def test_check_ok(self, send_ntf_mock, bc_mock):
        AccountFactory.create_batch(
            2, currency__name='BTC', balance=Decimal('0.2'))
        bc_mock.return_value = Mock(**{
            'get_balance.return_value': Decimal('0.4'),
            'get_address_balance.return_value': Decimal('0.2'),
        })
        check_wallet('mainnet')
        check_wallet_strict('mainnet')
        self.assertFalse(send_ntf_mock.called)

    @patch('website.management.commands.check_wallet.BlockChain')
    def test_check_mismatch(self, bc_mock):
        AccountFactory.create(
            currency__name='BTC',
            balance=Decimal('0.2'),
            bitcoin_address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        AccountFactory.create(
            currency__name='BTC',
            balance=Decimal('0.2'),
            bitcoin_address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa3p9vE')
        bc_mock.return_value = Mock(**{
            'get_address_balance.return_value': Decimal('0.3'),
        })
        check_wallet('mainnet')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(settings.CONTACT_EMAIL_RECIPIENTS[0],
                      mail.outbox[0].to)
        self.assertIn('mainnet', mail.outbox[0].body)

    @patch('website.management.commands.check_wallet.BlockChain')
    def test_strict_check_mismatch(self, bc_mock):
        AccountFactory.create_batch(
            2, currency__name='BTC', balance=Decimal('0.2'))
        bc_mock.return_value = Mock(**{
            'get_balance.return_value': Decimal('0.5'),
        })
        check_wallet_strict('mainnet')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(settings.CONTACT_EMAIL_RECIPIENTS[0],
                      mail.outbox[0].to)
        self.assertIn('mainnet', mail.outbox[0].body)


class WithdrawBTCTestCase(TestCase):

    @patch('website.management.commands.withdraw_btc.blockchain.BlockChain')
    def test_command(self, bc_cls_mock):
        account = AccountFactory.create(
            currency__name='BTC',
            balance=Decimal('0.2'),
            balance_max=Decimal('0.5'),
            bitcoin_address='1BESvTCjZG8jpK7Hvan7KzpXLFdaFRxWPk')
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_unspent_outputs.return_value': [
                {'amount': Decimal('0.2'), 'outpoint': outpoint_factory()},
            ],
            'create_raw_transaction.return_value': 'tx',
            'sign_raw_transaction.return_value': 'tx_signed',
            'send_raw_transaction.return_value': '0000',
        })
        result = withdraw_btc(
            account.pk,
            '1Mavf5uXXUNiJbvi5vmD4CjvFghTm9pZvM')
        self.assertEqual(
            result,
            'sent 0.19990000 BTC to 1Mavf5uXXUNiJbvi5vmD4CjvFghTm9pZvM, '
            'tx id 0000')
        self.assertEqual(bc_cls_mock.call_args[0][0], 'mainnet')
        self.assertTrue(bc_mock.send_raw_transaction.called)


class CryptoPaySyncTestCase(TestCase):

    @patch('website.management.commands.cryptopay_sync.update_managed_accounts')
    @patch('website.management.commands.cryptopay_sync.update_balances')
    def test_command(self, b_mock, a_mock):
        MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY)
        cryptopay_sync()
        self.assertEqual(a_mock.call_count, 1)
        self.assertEqual(b_mock.call_count, 1)

from decimal import Decimal
from StringIO import StringIO

from django.core.management import call_command
from django.test import TestCase

from mock import patch, Mock

from website.models import INSTANTFIAT_PROVIDERS
from website.tests.factories import (
    MerchantAccountFactory,
    AccountFactory,
    AddressFactory)
from website.management.commands.check_wallet_ import \
    check_wallet, check_wallet_strict
from website.management.commands.cryptopay_sync import cryptopay_sync
from operations.exceptions import CryptoPayInvalidAPIKey
from operations.tests.factories import outpoint_factory
from wallet.tests.factories import WalletKeyFactory


class CheckWalletTestCase(TestCase):

    @patch('website.management.commands.check_wallet_.BlockChain')
    @patch('website.management.commands.check_wallet_.logger')
    def test_check_ok(self, logger_mock, bc_cls_mock):
        account_1 = AccountFactory.create(
            currency__name='BTC', balance_=Decimal('0.2'))
        AddressFactory.create(account=account_1)
        account_2 = AccountFactory.create(
            currency__name='BTC', balance_=Decimal('0.2'))
        AddressFactory.create(account=account_2)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_balance.return_value': Decimal('0.4'),
            'get_address_balance.return_value': Decimal('0.2'),
        })
        check_wallet('mainnet')
        self.assertEqual(bc_mock.get_address_balance.call_count, 2)
        check_wallet_strict('mainnet')
        self.assertEqual(bc_mock.get_balance.call_count, 1)
        self.assertIs(logger_mock.critical.called, False)
        self.assertIs(logger_mock.info.called, True)

    @patch('website.management.commands.check_wallet_.BlockChain')
    @patch('website.management.commands.check_wallet_.logger')
    def test_check_mismatch(self, logger_mock, bc_cls_mock):
        account = AccountFactory.create(
            currency__name='BTC', balance_=Decimal('0.2'))
        address = AddressFactory.create(account=account)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_address_balance.return_value': Decimal('0.3'),
        })
        check_wallet('mainnet')
        self.assertEqual(bc_mock.get_address_balance.call_args[0][0],
                         address.address)
        self.assertIs(logger_mock.critical.called, True)

    @patch('website.management.commands.check_wallet_.BlockChain')
    @patch('website.management.commands.check_wallet_.logger')
    def test_strict_check_mismatch(self, logger_mock, bc_cls_mock):
        AccountFactory.create_batch(
            2, currency__name='BTC', balance_=Decimal('0.2'))
        bc_cls_mock.return_value = Mock(**{
            'get_balance.return_value': Decimal('0.5'),
        })
        check_wallet_strict('mainnet')
        self.assertIs(logger_mock.critical.called, True)


class CryptoPaySyncTestCase(TestCase):

    @patch('website.management.commands.cryptopay_sync.update_managed_accounts')
    @patch('website.management.commands.cryptopay_sync.update_balances')
    @patch('website.management.commands.cryptopay_sync.check_documents')
    def test_command(self, c_mock, b_mock, a_mock):
        MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.GOCOIN)
        MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY)
        MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_api_key=None)
        MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='xxx',
            verification_status='pending')
        messages = list(cryptopay_sync())
        self.assertEqual(a_mock.call_count, 2)
        self.assertEqual(b_mock.call_count, 2)
        self.assertEqual(c_mock.call_count, 1)
        self.assertEqual(len(messages), 2)

    @patch('website.management.commands.cryptopay_sync.update_managed_accounts')
    def test_invalid_api_key(self, update_mock):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY)
        self.assertIsNotNone(merchant.instantfiat_api_key)
        update_mock.side_effect = CryptoPayInvalidAPIKey
        messages = list(cryptopay_sync())
        merchant.refresh_from_db()
        self.assertIsNone(merchant.instantfiat_api_key)
        self.assertEqual(len(messages), 1)


class MigrateWalletTestCase(TestCase):

    def setUp(self):
        WalletKeyFactory()

    @patch('website.management.commands.migrate_wallet.BlockChain')
    @patch('website.management.commands.migrate_wallet.run_periodic_task')
    def test_migrate(self, run_task_mock, bc_cls_mock):
        account = AccountFactory(currency__name='BTC')
        address = AddressFactory(account=account)
        transfer_tx_id = '1' * 64
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_unspent_outputs.side_effect': [
                [{'amount': Decimal('0.2'), 'outpoint': outpoint_factory()}],
                [{'amount': Decimal('0.002'), 'outpoint': outpoint_factory()}],
            ],
            'get_tx_fee.return_value': Decimal('0.0005'),
            'create_raw_transaction.return_value': 'tx',
            'sign_raw_transaction.return_value': 'tx_signed',
            'send_raw_transaction.return_value': transfer_tx_id,
        })
        fee_address = 'test_address'
        buffer = StringIO()
        call_command('migrate_wallet', 'BTC', fee_address, stdout=buffer)

        self.assertEqual(bc_mock.get_unspent_outputs.call_count, 2)
        self.assertEqual(bc_mock.get_unspent_outputs.call_args_list[0][0][0],
                         address.address)
        self.assertEqual(bc_mock.get_unspent_outputs.call_args_list[1][0][0],
                         fee_address)
        self.assertEqual(bc_mock.import_address.call_count, 1)
        self.assertEqual(account.deposit_set.count(), 1)
        deposit = account.deposit_set.get()
        self.assertEqual(deposit.merchant_coin_amount, Decimal('0.2'))
        self.assertEqual(deposit.fee_coin_amount, 0)
        self.assertIsNotNone(deposit.time_notified)
        self.assertEqual(bc_mock.get_tx_fee.call_args[0], (2, 2))
        tx_inputs = bc_mock.create_raw_transaction.call_args[0][0]
        self.assertEqual(len(tx_inputs), 2)
        tx_outputs = bc_mock.create_raw_transaction.call_args[0][1]
        self.assertEqual(tx_outputs, {
            deposit.deposit_address.address: Decimal('0.2'),
            fee_address: Decimal('0.0015'),
        })
        self.assertEqual(run_task_mock.call_count, 2)
        self.assertEqual(run_task_mock.call_args_list[0][0][0].__name__,
                         'wait_for_payment')
        self.assertEqual(run_task_mock.call_args_list[1][0][0].__name__,
                         'check_deposit_status')
        self.assertIn(transfer_tx_id, buffer.getvalue())

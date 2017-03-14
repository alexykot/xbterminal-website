from decimal import Decimal

from django.test import TestCase
from mock import patch, Mock

from website.models import INSTANTFIAT_PROVIDERS
from website.tests.factories import (
    MerchantAccountFactory,
    AccountFactory,
    AddressFactory)
from website.management.commands.check_wallet import \
    check_wallet, check_wallet_strict
from website.management.commands.withdraw_btc import withdraw_btc
from website.management.commands.cryptopay_sync import cryptopay_sync
from operations.exceptions import CryptoPayInvalidAPIKey
from operations.tests.factories import outpoint_factory


class CheckWalletTestCase(TestCase):

    @patch('website.management.commands.check_wallet.BlockChain')
    @patch('website.management.commands.check_wallet.logger')
    def test_check_ok(self, logger_mock, bc_cls_mock):
        account_1 = AccountFactory.create(
            currency__name='BTC', balance=Decimal('0.2'))
        AddressFactory.create(account=account_1)
        account_2 = AccountFactory.create(
            currency__name='BTC', balance=Decimal('0.2'))
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

    @patch('website.management.commands.check_wallet.BlockChain')
    @patch('website.management.commands.check_wallet.logger')
    def test_check_mismatch(self, logger_mock, bc_cls_mock):
        account = AccountFactory.create(
            currency__name='BTC', balance=Decimal('0.2'))
        address = AddressFactory.create(account=account)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_address_balance.return_value': Decimal('0.3'),
        })
        check_wallet('mainnet')
        self.assertEqual(bc_mock.get_address_balance.call_args[0][0],
                         address.address)
        self.assertIs(logger_mock.critical.called, True)

    @patch('website.management.commands.check_wallet.BlockChain')
    @patch('website.management.commands.check_wallet.logger')
    def test_strict_check_mismatch(self, logger_mock, bc_cls_mock):
        AccountFactory.create_batch(
            2, currency__name='BTC', balance=Decimal('0.2'))
        bc_cls_mock.return_value = Mock(**{
            'get_balance.return_value': Decimal('0.5'),
        })
        check_wallet_strict('mainnet')
        self.assertIs(logger_mock.critical.called, True)


class WithdrawBTCTestCase(TestCase):

    @patch('website.management.commands.withdraw_btc.blockchain.BlockChain')
    def test_command(self, bc_cls_mock):
        account = AccountFactory.create(
            currency__name='BTC',
            balance=Decimal('0.2'),
            balance_max=Decimal('0.5'))
        address = AddressFactory.create(account=account)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_unspent_outputs.return_value': [
                {'amount': Decimal('0.2'), 'outpoint': outpoint_factory()},
            ],
            'create_raw_transaction.return_value': 'tx',
            'sign_raw_transaction.return_value': 'tx_signed',
            'send_raw_transaction.return_value': '0000',
            'get_tx_fee.return_value': Decimal('0.0005'),
        })
        result = withdraw_btc(
            account.pk,
            '1Mavf5uXXUNiJbvi5vmD4CjvFghTm9pZvM')
        self.assertEqual(
            result,
            'sent 0.19950000 BTC to 1Mavf5uXXUNiJbvi5vmD4CjvFghTm9pZvM, '
            'tx id 0000')
        self.assertEqual(bc_cls_mock.call_args[0][0], 'mainnet')
        self.assertEqual(bc_mock.get_unspent_outputs.call_args[0][0],
                         address.address)
        self.assertTrue(bc_mock.send_raw_transaction.called)
        self.assertEqual(bc_mock.get_tx_fee.call_args[0], (1, 1))


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

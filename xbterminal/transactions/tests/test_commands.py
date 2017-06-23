from decimal import Decimal

from django.test import TestCase
from django.core.management import call_command

from mock import patch, Mock

from transactions.tests.factories import (
    DepositFactory,
    BalanceChangeFactory,
    NegativeBalanceChangeFactory)
from wallet.tests.factories import WalletAccountFactory


class CheckWalletTestCase(TestCase):

    @patch('transactions.management.commands.check_wallet_.BlockChain')
    @patch('transactions.management.commands.check_wallet_.logger')
    def test_balance_ok(self, logger_mock, bc_cls_mock):
        wallet_account = WalletAccountFactory()
        bch_1, bch_2 = BalanceChangeFactory.create_batch(
            2, deposit__deposit_address__wallet_account=wallet_account)
        deposit = DepositFactory(
            deposit_address__wallet_account=wallet_account)
        bch_3 = BalanceChangeFactory(
            deposit=deposit,
            amount=deposit.merchant_coin_amount)
        bch_4 = BalanceChangeFactory(
            deposit=deposit,
            account=None,
            amount=deposit.fee_coin_amount)
        bch_5 = NegativeBalanceChangeFactory(
            withdrawal__account=deposit.account,
            withdrawal__customer_coin_amount=bch_3.amount / 2,
            address=deposit.deposit_address)
        expected_balance = bch_1.amount + bch_2.amount + bch_3.amount + \
            bch_4.amount + bch_5.amount
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_address_balance.side_effect': [
                bch_1.amount,
                bch_2.amount,
                bch_3.amount + bch_4.amount + bch_5.amount,
            ],
        })
        call_command('check_wallet_', 'BTC')

        self.assertEqual(bc_cls_mock.call_args[0][0], 'mainnet')
        self.assertEqual(bc_mock.get_address_balance.call_count, 3)
        self.assertIs(logger_mock.info.called, True)
        self.assertEqual(logger_mock.info.call_args[0][1], 'BTC')
        self.assertEqual(logger_mock.info.call_args[0][2], expected_balance)

    @patch('transactions.management.commands.check_wallet_.BlockChain')
    @patch('transactions.management.commands.check_wallet_.logger')
    def test_balance_mismatch(self, logger_mock, bc_cls_mock):
        bch = BalanceChangeFactory()
        wallet_balance = Decimal('0.01')
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_address_balance.return_value': wallet_balance,
        })
        call_command('check_wallet_', 'BTC')

        self.assertEqual(bc_mock.get_address_balance.call_count, 1)
        self.assertIs(logger_mock.critical.called, True)
        self.assertEqual(logger_mock.critical.call_args[0][2], wallet_balance)
        self.assertEqual(logger_mock.critical.call_args[0][3], bch.amount)

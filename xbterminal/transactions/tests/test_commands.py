from decimal import Decimal
from StringIO import StringIO

from django.test import TestCase
from django.core.management import call_command

from mock import patch, Mock

from transactions.tests.factories import (
    DepositFactory,
    BalanceChangeFactory,
    NegativeBalanceChangeFactory)


class CheckWalletTestCase(TestCase):

    @patch('transactions.management.commands.check_wallet.BlockChain')
    @patch('transactions.management.commands.check_wallet.logger')
    def test_balance_ok(self, logger_mock, bc_cls_mock):
        bch_1, bch_2 = BalanceChangeFactory.create_batch(2)
        deposit = DepositFactory(
            amount=Decimal('0.01'),
            exchange_rate=Decimal('1000.0'))
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
        buffer = StringIO()
        call_command('check_wallet', 'BTC', stdout=buffer)

        self.assertEqual(bc_cls_mock.call_args[0][0], 'BTC')
        self.assertEqual(bc_mock.get_address_balance.call_count, 3)
        self.assertIs(logger_mock.info.call_count, 0)
        output = buffer.getvalue().splitlines()
        self.assertEqual(
            output[0],
            'BTC: total balance {}'.format(expected_balance))
        self.assertEqual(output[1], 'BTC: address pool size 3')

    @patch('transactions.management.commands.check_wallet.BlockChain')
    @patch('transactions.management.commands.check_wallet.logger')
    def test_balance_mismatch(self, logger_mock, bc_cls_mock):
        bch = BalanceChangeFactory()
        wallet_balance = Decimal('0.01')
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_address_balance.return_value': wallet_balance,
        })
        buffer = StringIO()
        call_command('check_wallet', 'BTC', stdout=buffer)

        self.assertEqual(bc_mock.get_address_balance.call_count, 1)
        self.assertIs(logger_mock.critical.called, True)
        self.assertEqual(logger_mock.critical.call_args[0][2], wallet_balance)
        self.assertEqual(logger_mock.critical.call_args[0][3], bch.amount)
        output = buffer.getvalue().splitlines()
        self.assertEqual(
            output[0],
            'BTC: balance mismatch, {0} != {1}'.format(
                wallet_balance, bch.amount))
        self.assertEqual(output[1], 'BTC: address pool size 1')

    @patch('transactions.management.commands.check_wallet.check_wallet')
    def test_all_coins(self, check_wallet_mock):
        call_command('check_wallet')

        currencies = set(call[0][0].name for call in
                         check_wallet_mock.call_args_list)
        self.assertEqual(currencies, {'BTC', 'TBTC', 'DASH', 'TDASH'})

    @patch('transactions.management.commands.check_wallet.check_wallet')
    def test_invalid_currency_name(self, check_wallet_mock):
        buffer = StringIO()
        call_command('check_wallet', 'XXX', stdout=buffer)

        self.assertIn('invalid currency name', buffer.getvalue())
        self.assertIs(check_wallet_mock.called, False)

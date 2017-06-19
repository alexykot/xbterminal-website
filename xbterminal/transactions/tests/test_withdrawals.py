from decimal import Decimal

from django.test import TestCase
from mock import patch, Mock

from transactions.models import get_account_balance, get_address_balance
from transactions.withdrawals import prepare_withdrawal
from transactions.tests.factories import DepositFactory
from operations.exceptions import WithdrawalError
from wallet.constants import BIP44_COIN_TYPES
from website.tests.factories import DeviceFactory


class PrepareWithdrawalTestCase(TestCase):

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_prepare(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory(max_payout=Decimal('50.0'))
        deposit = DepositFactory(
            received=True,
            account=device.account,
            fee_coin_amount=0,
            paid_coin_amount=Decimal('0.01'))
        deposit.create_balance_changes()
        get_rate_mock.return_value = Decimal('2000.00')
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_tx_fee.return_value': Decimal('0.001'),
        })
        amount = Decimal('10.0')
        withdrawal = prepare_withdrawal(device, amount)

        self.assertEqual(get_rate_mock.call_args[0][0],
                         withdrawal.currency.name)
        self.assertEqual(bc_mock.get_tx_fee.call_count, 1)
        self.assertEqual(withdrawal.account, device.account)
        self.assertEqual(withdrawal.device, device)
        self.assertEqual(withdrawal.currency,
                         device.account.merchant.currency)
        self.assertEqual(withdrawal.amount, amount)
        self.assertEqual(withdrawal.coin_type, BIP44_COIN_TYPES.BTC)
        self.assertEqual(withdrawal.customer_coin_amount, Decimal('0.005'))
        self.assertEqual(withdrawal.tx_fee_coin_amount, Decimal('0.001'))
        self.assertEqual(withdrawal.status, 'new')

        self.assertEqual(get_account_balance(device.account),
                         Decimal('0.004'))
        self.assertEqual(withdrawal.balancechange_set.count(), 2)
        change_1 = withdrawal.balancechange_set.get(amount__lt=0)
        self.assertEqual(change_1.account, withdrawal.account)
        self.assertEqual(change_1.address, deposit.deposit_address)
        self.assertEqual(change_1.amount, -deposit.paid_coin_amount)
        self.assertEqual(get_address_balance(change_1.address), 0)
        change_2 = withdrawal.balancechange_set.get(amount__gt=0)
        self.assertEqual(change_2.account, withdrawal.account)
        self.assertIs(change_2.address.is_change, True)
        self.assertEqual(change_2.amount, Decimal('0.004'))
        self.assertEqual(get_address_balance(change_2.address),
                         Decimal('0.004'))

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_from_multiple_addresses(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory(max_payout=Decimal('50.0'))
        deposit_1 = DepositFactory(
            received=True,
            account=device.account,
            fee_coin_amount=0,
            paid_coin_amount=Decimal('0.01'))
        deposit_1.create_balance_changes()
        deposit_2 = DepositFactory(
            received=True,
            account=device.account,
            deposit_address__wallet_account=deposit_1.deposit_address.wallet_account,
            fee_coin_amount=0,
            paid_coin_amount=Decimal('0.01'))
        deposit_2.create_balance_changes()
        get_rate_mock.return_value = Decimal('2000.00')
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_tx_fee.return_value': Decimal('0.001'),
        })
        amount = Decimal('30.0')
        withdrawal = prepare_withdrawal(device, amount)

        self.assertEqual(bc_mock.get_tx_fee.call_count, 2)
        self.assertEqual(withdrawal.coin_amount, Decimal('0.016'))
        self.assertEqual(withdrawal.balancechange_set.count(), 3)
        self.assertEqual(get_account_balance(device.account),
                         Decimal('0.004'))
        self.assertEqual(get_address_balance(deposit_1.deposit_address), 0)
        self.assertEqual(get_address_balance(deposit_2.deposit_address), 0)
        change_address = withdrawal.balancechange_set.get(amount__gt=0).address
        self.assertEqual(get_address_balance(change_address), Decimal('0.004'))

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_max_payout(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory.create(max_payout=Decimal('10.0'))
        get_rate_mock.return_value = Decimal('2000.00')
        amount = Decimal('100.00')
        with self.assertRaises(WithdrawalError) as context:
            prepare_withdrawal(device, amount)
        self.assertEqual(context.exception.message,
                         'Amount exceeds max payout for current device')

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_dust_threshold(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory(max_payout=Decimal('10.0'))
        get_rate_mock.return_value = Decimal('2000.0')
        amount = Decimal('0.05')
        with self.assertRaises(WithdrawalError) as context:
            prepare_withdrawal(device, amount)
        self.assertEqual(context.exception.message,
                         'Customer coin amount is below dust threshold')

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_no_addresses(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory.create(max_payout=Decimal('10.0'))
        get_rate_mock.return_value = Decimal('2000.00')
        amount = Decimal('1.00')
        with self.assertRaises(WithdrawalError) as context:
            prepare_withdrawal(device, amount)
        self.assertEqual(context.exception.message,
                         'Insufficient balance in wallet')

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_insufficient_account_balance(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory(max_payout=Decimal('50.0'))
        deposit = DepositFactory(
            received=True,
            fee_coin_amount=0,
            paid_coin_amount=Decimal('0.01'))
        deposit.create_balance_changes()
        get_rate_mock.return_value = Decimal('2000.00')
        bc_cls_mock.return_value = Mock(**{
            'get_tx_fee.return_value': Decimal('0.001'),
        })
        amount = Decimal('10.0')
        with self.assertRaises(WithdrawalError) as context:
            prepare_withdrawal(device, amount)
        self.assertEqual(context.exception.message,
                         'Insufficient balance on merchant account')

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_already_reserved(self, get_rate_mock, bc_cls_mock):
        pass

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_dust_change(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory(max_payout=Decimal('50.0'))
        deposit = DepositFactory(
            received=True,
            account=device.account,
            fee_coin_amount=0,
            paid_coin_amount=Decimal('0.011001'))
        deposit.create_balance_changes()
        get_rate_mock.return_value = Decimal('2000.00')
        bc_cls_mock.return_value = Mock(**{
            'get_tx_fee.return_value': Decimal('0.001'),
        })
        amount = Decimal('20.0')
        withdrawal = prepare_withdrawal(device, amount)

        self.assertIs(
            withdrawal.balancechange_set.filter(amount__gt=0).exists(),
            False)  # No change
        self.assertEqual(withdrawal.customer_coin_amount, Decimal('0.010001'))
        self.assertEqual(withdrawal.coin_amount, deposit.paid_coin_amount)

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_prepare_no_device(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory(max_payout=Decimal('50.0'))
        deposit = DepositFactory(
            received=True,
            account=device.account,
            fee_coin_amount=0,
            paid_coin_amount=Decimal('0.01'))
        deposit.create_balance_changes()
        get_rate_mock.return_value = Decimal('2000.00')
        bc_cls_mock.return_value = Mock(**{
            'get_tx_fee.return_value': Decimal('0.001'),
        })
        amount = Decimal('10.0')
        withdrawal = prepare_withdrawal(device.account, amount)

        self.assertIsNone(withdrawal.device)
        self.assertEqual(withdrawal.account, device.account)

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from mock import patch, Mock

from transactions.models import get_account_balance, get_address_balance
from transactions.withdrawals import (
    prepare_withdrawal,
    send_transaction,
    wait_for_confidence,
    wait_for_confirmation)
from transactions.tests.factories import (
    WithdrawalFactory,
    BalanceChangeFactory,
    NegativeBalanceChangeFactory)
from operations.exceptions import WithdrawalError, TransactionModified
from wallet.constants import BIP44_COIN_TYPES
from wallet.tests.factories import WalletAccountFactory
from website.tests.factories import DeviceFactory


class PrepareWithdrawalTestCase(TestCase):

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_prepare(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory(max_payout=Decimal('50.0'))
        bch_0 = BalanceChangeFactory(
            deposit__confirmed=True,
            deposit__account=device.account,
            deposit__merchant_coin_amount=Decimal('0.01'))
        get_rate_mock.return_value = Decimal('2000.00')
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_tx_fee.return_value': Decimal('0.001'),
        })
        amount = Decimal('10.0')
        withdrawal = prepare_withdrawal(device, amount)

        self.assertEqual(get_rate_mock.call_args[0][0],
                         withdrawal.currency.name)
        self.assertEqual(bc_mock.get_tx_fee.call_count, 1)
        self.assertEqual(bc_mock.import_address.call_count, 1)
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
        self.assertEqual(get_account_balance(device.account,
                                             only_confirmed=True), 0)
        self.assertEqual(withdrawal.balancechange_set.count(), 2)
        bch_1 = withdrawal.balancechange_set.get(amount__lt=0)
        self.assertEqual(bch_1.account, withdrawal.account)
        self.assertEqual(bch_1.address, bch_0.address)
        self.assertEqual(bch_1.amount, -bch_0.amount)
        self.assertEqual(get_address_balance(bch_1.address), 0)
        self.assertEqual(get_address_balance(bch_1.address,
                                             only_confirmed=True), 0)
        bch_2 = withdrawal.balancechange_set.get(amount__gt=0)
        self.assertEqual(bch_2.account, withdrawal.account)
        self.assertIs(bch_2.address.is_change, True)
        self.assertEqual(bc_mock.import_address.call_args[0][0],
                         bch_2.address.address)
        self.assertEqual(bch_2.amount, Decimal('0.004'))
        self.assertEqual(get_address_balance(bch_2.address),
                         Decimal('0.004'))
        self.assertEqual(get_address_balance(bch_1.address,
                                             only_confirmed=True), 0)

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_from_multiple_addresses(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory(max_payout=Decimal('50.0'))
        wallet_account = WalletAccountFactory()
        bch_1 = BalanceChangeFactory(
            deposit__confirmed=True,
            deposit__account=device.account,
            deposit__deposit_address__wallet_account=wallet_account,
            deposit__merchant_coin_amount=Decimal('0.01'))
        bch_2 = BalanceChangeFactory(
            deposit__confirmed=True,
            deposit__account=device.account,
            deposit__deposit_address__wallet_account=wallet_account,
            deposit__merchant_coin_amount=Decimal('0.01'))
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
        self.assertEqual(get_address_balance(bch_1.address), 0)
        self.assertEqual(get_address_balance(bch_2.address), 0)
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
        BalanceChangeFactory(
            deposit__confirmed=True,
            deposit__merchant_coin_amount=Decimal('0.01'))
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
    def test_already_reserved(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory(max_payout=Decimal('50.0'))
        wallet_account = WalletAccountFactory()
        bch_1 = BalanceChangeFactory(
            deposit__confirmed=True,
            deposit__account=device.account,
            deposit__deposit_address__wallet_account=wallet_account,
            deposit__merchant_coin_amount=Decimal('0.01'))
        bch_2 = BalanceChangeFactory(  # noqa: F841
            deposit__confirmed=True,
            deposit__account=device.account,
            deposit__deposit_address__wallet_account=wallet_account,
            deposit__merchant_coin_amount=Decimal('0.01'))
        bch_3 = NegativeBalanceChangeFactory(  # noqa: F841
            withdrawal__account=device.account,
            withdrawal__customer_coin_amount=bch_1.amount,
            address=bch_1.address)
        get_rate_mock.return_value = Decimal('2000.00')
        bc_cls_mock.return_value = Mock(**{
            'get_tx_fee.return_value': Decimal('0.001'),
        })
        amount = Decimal('20.0')
        with self.assertRaises(WithdrawalError) as context:
            prepare_withdrawal(device, amount)
        self.assertEqual(context.exception.message,
                         'Insufficient balance in wallet')

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_dust_change(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory(max_payout=Decimal('50.0'))
        bch = BalanceChangeFactory(
            deposit__confirmed=True,
            deposit__account=device.account,
            deposit__merchant_coin_amount=Decimal('0.011001'))
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
        self.assertEqual(withdrawal.coin_amount, bch.amount)

    @patch('transactions.withdrawals.get_exchange_rate')
    @patch('transactions.withdrawals.BlockChain')
    def test_prepare_no_device(self, bc_cls_mock, get_rate_mock):
        device = DeviceFactory(max_payout=Decimal('50.0'))
        BalanceChangeFactory(
            deposit__confirmed=True,
            deposit__account=device.account,
            deposit__merchant_coin_amount=Decimal('0.01'))
        get_rate_mock.return_value = Decimal('2000.00')
        bc_cls_mock.return_value = Mock(**{
            'get_tx_fee.return_value': Decimal('0.001'),
        })
        amount = Decimal('10.0')
        withdrawal = prepare_withdrawal(device.account, amount)

        self.assertIsNone(withdrawal.device)
        self.assertEqual(withdrawal.account, device.account)


class SendTransactionTestCase(TestCase):

    @patch('transactions.withdrawals.BlockChain')
    @patch('transactions.withdrawals.create_tx_')
    @patch('transactions.withdrawals.run_periodic_task')
    def test_send(self, run_task_mock, create_tx_mock, bc_cls_mock):
        withdrawal = WithdrawalFactory(
            customer_coin_amount=Decimal('0.01'))
        wallet_account = WalletAccountFactory()
        bch_1 = NegativeBalanceChangeFactory(
            withdrawal=withdrawal,
            address__wallet_account=wallet_account,
            amount=Decimal('-0.01'))
        bch_2 = NegativeBalanceChangeFactory(
            withdrawal=withdrawal,
            address__wallet_account=wallet_account,
            amount=Decimal('0.02'))
        customer_address = '1NdS5JCXzbhNv4STQAaknq56iGstfgRCXg'
        outgoing_tx_id = '0' * 64
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_raw_unspent_outputs.return_value': [
                {'txid': '1' * 64, 'amount': Decimal('0.002')},
                {'txid': '2' * 64, 'amount': Decimal('0.008')},
            ],
            'send_raw_transaction.return_value': outgoing_tx_id,
        })
        create_tx_mock.return_value = tx_mock = Mock()
        send_transaction(withdrawal, customer_address)

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.customer_address, customer_address)
        self.assertEqual(withdrawal.outgoing_tx_id, outgoing_tx_id)
        self.assertEqual(withdrawal.status, 'sent')
        self.assertEqual(bc_mock.get_raw_unspent_outputs.call_count, 1)
        self.assertEqual(bc_mock.get_raw_unspent_outputs.call_args[0][0],
                         bch_1.address.address)
        self.assertEqual(bc_mock.get_raw_unspent_outputs.call_args[1]['minconf'], 6)
        tx_inputs = create_tx_mock.call_args[0][0]
        self.assertEqual(len(tx_inputs), 2)
        self.assertEqual(tx_inputs[0]['txid'], '1' * 64)
        self.assertEqual(tx_inputs[0]['private_key'].hwif(),
                         bch_1.address.get_private_key().hwif())
        tx_outputs = create_tx_mock.call_args[0][1]
        self.assertEqual(len(tx_outputs.keys()), 2)
        self.assertEqual(tx_outputs[customer_address],
                         abs(bch_1.amount))
        self.assertEqual(tx_outputs[bch_2.address.address],
                         bch_2.amount)
        self.assertEqual(bc_mock.send_raw_transaction.call_args[0][0],
                         tx_mock)
        self.assertEqual(run_task_mock.call_args[0][0].__name__,
                         'wait_for_confidence')
        self.assertEqual(run_task_mock.call_args[0][1], [withdrawal.pk])

    @patch('transactions.withdrawals.BlockChain')
    @patch('transactions.withdrawals.create_tx_')
    @patch('transactions.withdrawals.run_periodic_task')
    def test_send_without_change(self, run_task_mock, create_tx_mock, bc_cls_mock):
        withdrawal = WithdrawalFactory()
        NegativeBalanceChangeFactory(withdrawal=withdrawal)
        customer_address = '1NdS5JCXzbhNv4STQAaknq56iGstfgRCXg'
        outgoing_tx_id = '0' * 64
        bc_cls_mock.return_value = Mock(**{
            'get_raw_unspent_outputs.return_value': [{
                'txid': '1' * 64,
                'amount': withdrawal.coin_amount,
            }],
            'send_raw_transaction.return_value': outgoing_tx_id,
        })
        create_tx_mock.return_value = Mock()
        send_transaction(withdrawal, customer_address)

        withdrawal.refresh_from_db()
        tx_outputs = create_tx_mock.call_args[0][1]
        self.assertEqual(len(tx_outputs.keys()), 1)
        self.assertEqual(tx_outputs[customer_address],
                         withdrawal.customer_coin_amount)

    def test_invalid_customer_address(self):
        withdrawal = WithdrawalFactory()
        customer_address = 'mhXPmYBSUsjEKmyi568cEoZYR3QHHkhMyG'
        with self.assertRaises(WithdrawalError):
            send_transaction(withdrawal, customer_address)

    @patch('transactions.withdrawals.BlockChain')
    def test_address_balance_error(self, bc_cls_mock):
        withdrawal = WithdrawalFactory(
            customer_coin_amount=Decimal('0.01'))
        NegativeBalanceChangeFactory(withdrawal=withdrawal)
        customer_address = '1NdS5JCXzbhNv4STQAaknq56iGstfgRCXg'
        bc_cls_mock.return_value = Mock(**{
            'get_raw_unspent_outputs.return_value': [{
                'txid': '1' * 64,
                'amount': Decimal('0.015'),
            }],
        })
        with self.assertRaises(WithdrawalError) as context:
            send_transaction(withdrawal, customer_address)
        self.assertEqual(context.exception.message,
                         'Error in address balance')


class WaitForConfidenceTestCase(TestCase):

    @patch('transactions.withdrawals.cancel_current_task')
    def test_already_broadcasted(self, cancel_mock):
        withdrawal = WithdrawalFactory(
            sent=True,
            time_broadcasted=timezone.now())
        wait_for_confidence(withdrawal.pk)
        self.assertIs(cancel_mock.called, True)

    @patch('transactions.withdrawals.BlockChain')
    @patch('transactions.withdrawals.is_tx_reliable')
    @patch('transactions.withdrawals.cancel_current_task')
    @patch('transactions.withdrawals.run_periodic_task')
    def test_tx_confirmed(self, run_task_mock, cancel_mock,
                          is_reliable_mock, bc_cls_mock):
        withdrawal = WithdrawalFactory(sent=True)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.return_value': True,
        })
        is_reliable_mock.return_value = True
        wait_for_confidence(withdrawal.pk)

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'broadcasted')
        self.assertIs(bc_mock.is_tx_confirmed.called, True)
        self.assertIs(is_reliable_mock.called, False)
        self.assertIs(cancel_mock.called, True)
        self.assertEqual(run_task_mock.call_args[0][0].__name__,
                         'wait_for_confirmation')
        self.assertEqual(run_task_mock.call_args[0][1], [withdrawal.pk])

    @patch('transactions.withdrawals.BlockChain')
    @patch('transactions.withdrawals.is_tx_reliable')
    @patch('transactions.withdrawals.cancel_current_task')
    @patch('transactions.withdrawals.run_periodic_task')
    def test_tx_broadcasted(self, run_task_mock, cancel_mock,
                            is_reliable_mock, bc_cls_mock):
        withdrawal = WithdrawalFactory(sent=True)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.return_value': False,
        })
        is_reliable_mock.return_value = True
        wait_for_confidence(withdrawal.pk)

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'broadcasted')
        self.assertIs(bc_mock.is_tx_confirmed.called, True)
        self.assertIs(is_reliable_mock.called, True)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(run_task_mock.called, True)

    @patch('transactions.withdrawals.BlockChain')
    @patch('transactions.withdrawals.is_tx_reliable')
    @patch('transactions.withdrawals.cancel_current_task')
    @patch('transactions.withdrawals.run_periodic_task')
    def test_tx_not_broadcasted(self, run_task_mock, cancel_mock,
                                is_reliable_mock, bc_cls_mock):
        withdrawal = WithdrawalFactory(sent=True)
        bc_cls_mock.return_value = Mock(**{
            'is_tx_confirmed.return_value': False,
        })
        is_reliable_mock.return_value = False
        wait_for_confidence(withdrawal.pk)

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'sent')
        self.assertIs(cancel_mock.called, False)
        self.assertIs(run_task_mock.called, False)

    @patch('transactions.withdrawals.BlockChain')
    @patch('transactions.withdrawals.is_tx_reliable')
    @patch('transactions.withdrawals.cancel_current_task')
    def test_tx_modified(self, cancel_mock, is_reliable_mock, bc_cls_mock):
        withdrawal = WithdrawalFactory(sent=True)
        final_tx_id = 'e' * 64
        bc_cls_mock.return_value = Mock(**{
            'is_tx_confirmed.side_effect': TransactionModified(final_tx_id),
        })
        is_reliable_mock.return_value = False
        wait_for_confidence(withdrawal.pk)

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'sent')
        self.assertEqual(withdrawal.outgoing_tx_id, final_tx_id)
        self.assertIs(is_reliable_mock.called, False)
        self.assertIs(cancel_mock.called, False)


class WaitForConfirmationTestCase(TestCase):

    @patch('transactions.withdrawals.BlockChain')
    @patch('transactions.withdrawals.cancel_current_task')
    def test_tx_confirmed(self, cancel_mock, bc_cls_mock):
        withdrawal = WithdrawalFactory(
            sent=True,
            time_broadcasted=timezone.now(),
            time_notified=timezone.now())
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.return_value': True,
        })
        wait_for_confirmation(withdrawal.pk)

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'confirmed')
        self.assertEqual(bc_mock.is_tx_confirmed.call_args[0][0],
                         withdrawal.outgoing_tx_id)
        self.assertIs(cancel_mock.called, True)

    @patch('transactions.withdrawals.BlockChain')
    @patch('transactions.withdrawals.cancel_current_task')
    def test_tx_not_confirmed(self, cancel_mock, bc_cls_mock):
        withdrawal = WithdrawalFactory(
            sent=True,
            time_broadcasted=timezone.now(),
            time_notified=timezone.now())
        bc_cls_mock.return_value = Mock(**{
            'is_tx_confirmed.return_value': False,
        })
        wait_for_confirmation(withdrawal.pk)

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'notified')
        self.assertIs(cancel_mock.called, False)

    @patch('transactions.withdrawals.BlockChain')
    @patch('transactions.withdrawals.cancel_current_task')
    def test_tx_modified(self, cancel_mock, bc_cls_mock):
        withdrawal = WithdrawalFactory(
            sent=True,
            time_broadcasted=timezone.now(),
            time_notified=timezone.now())
        final_tx_id = '1' * 64
        bc_cls_mock.return_value = Mock(**{
            'is_tx_confirmed.side_effect': TransactionModified(final_tx_id),
        })
        wait_for_confirmation(withdrawal.pk)

        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'notified')
        self.assertEqual(withdrawal.outgoing_tx_id, final_tx_id)
        self.assertIs(cancel_mock.called, False)

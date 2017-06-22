import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from mock import patch, Mock

from transactions.constants import PAYMENT_TYPES
from transactions.models import get_account_balance, get_address_balance
from transactions.deposits import (
    prepare_deposit,
    validate_payment,
    wait_for_payment,
    wait_for_confidence,
    wait_for_confirmation,
    refund_deposit,
    check_deposit_status)
from transactions.tests.factories import DepositFactory
from operations.exceptions import (
    InsufficientFunds,
    DoubleSpend,
    TransactionModified,
    RefundError)
from wallet.constants import BIP44_COIN_TYPES
from wallet.tests.factories import WalletKeyFactory
from website.tests.factories import AccountFactory, DeviceFactory


class PrepareDepositTestCase(TestCase):

    def setUp(self):
        WalletKeyFactory()

    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.get_exchange_rate')
    @patch('transactions.deposits.run_periodic_task')
    def test_prepare_with_device(self, run_task_mock, get_rate_mock, bc_cls_mock):
        device = DeviceFactory()
        bc_cls_mock.return_value = bc_mock = Mock()
        get_rate_mock.return_value = Decimal('2000.0')
        deposit = prepare_deposit(device, Decimal('10.00'))

        self.assertEqual(deposit.account, device.account)
        self.assertEqual(deposit.device, device)
        self.assertEqual(deposit.currency,
                         device.account.merchant.currency)
        self.assertEqual(deposit.amount, Decimal('10.00'))
        self.assertEqual(deposit.coin_type, BIP44_COIN_TYPES.BTC)
        self.assertIs(deposit.deposit_address.is_change, False)
        self.assertEqual(
            deposit.deposit_address.wallet_account.parent_key.coin_type,
            BIP44_COIN_TYPES.BTC)
        self.assertEqual(deposit.merchant_coin_amount, Decimal('0.005'))
        self.assertEqual(deposit.fee_coin_amount, Decimal('0.000025'))
        self.assertEqual(deposit.status, 'new')

        self.assertEqual(bc_mock.import_address.call_count, 1)
        self.assertEqual(bc_mock.import_address.call_args[0][0],
                         deposit.deposit_address.address)
        self.assertEqual(get_rate_mock.call_args[0][0],
                         deposit.currency.name)
        self.assertEqual(run_task_mock.call_count, 2)
        self.assertEqual(run_task_mock.call_args_list[0][0][0].__name__,
                         'wait_for_payment')
        self.assertEqual(run_task_mock.call_args_list[0][0][1], [deposit.pk])
        self.assertEqual(run_task_mock.call_args_list[1][0][0].__name__,
                         'check_deposit_status')
        self.assertEqual(run_task_mock.call_args_list[1][0][1], [deposit.pk])

    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.get_exchange_rate')
    @patch('transactions.deposits.run_periodic_task')
    def test_prepare_with_account(self, run_task_mock, get_rate_mock, bc_cls_mock):
        account = AccountFactory()
        get_rate_mock.return_value = Decimal('2000.0')
        deposit = prepare_deposit(account, Decimal('10.00'))

        self.assertEqual(deposit.account, account)
        self.assertIsNone(deposit.device)
        self.assertEqual(deposit.currency,
                         account.merchant.currency)
        self.assertEqual(deposit.coin_type, BIP44_COIN_TYPES.BTC)
        self.assertEqual(
            deposit.deposit_address.wallet_account.parent_key.coin_type,
            BIP44_COIN_TYPES.BTC)
        self.assertEqual(run_task_mock.call_count, 2)


class ValidatePaymentTestCase(TestCase):

    @patch('transactions.deposits.BlockChain')
    def test_validate(self, bc_cls_mock):
        deposit = DepositFactory()
        transactions = [Mock()]
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_tx_outputs.return_value': [{
                'address': deposit.deposit_address.address,
                'amount': deposit.coin_amount,
            }],
        })

        validate_payment(deposit, transactions)
        self.assertEqual(bc_mock.sign_raw_transaction.call_count, 1)
        deposit.refresh_from_db()
        self.assertEqual(deposit.paid_coin_amount, deposit.coin_amount)
        self.assertEqual(deposit.status, 'new')
        self.assertEqual(get_account_balance(deposit.account),
                         deposit.paid_coin_amount - deposit.fee_coin_amount)
        self.assertEqual(get_address_balance(deposit.deposit_address),
                         deposit.paid_coin_amount)

    @patch('transactions.deposits.BlockChain')
    def test_validate_multiple_tx(self, bc_cls_mock):
        deposit = DepositFactory(
            merchant_coin_amount=Decimal('0.1'),
            fee_coin_amount=Decimal('0.01'),
            paid_coin_amount=Decimal('0.05'))
        deposit.create_balance_changes()
        self.assertEqual(deposit.status, 'underpaid')
        transactions = [Mock(), Mock()]
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_tx_outputs.side_effect': [
                [{
                    'address': deposit.deposit_address.address,
                    'amount': Decimal('0.05'),
                }],
                [{
                    'address': deposit.deposit_address.address,
                    'amount': Decimal('0.1'),
                }],
            ],
        })

        validate_payment(deposit, transactions)
        self.assertEqual(bc_mock.sign_raw_transaction.call_count, 2)
        deposit.refresh_from_db()
        self.assertEqual(deposit.paid_coin_amount, Decimal('0.15'))
        self.assertEqual(get_account_balance(deposit.account),
                         deposit.paid_coin_amount - deposit.fee_coin_amount)
        self.assertEqual(get_address_balance(deposit.deposit_address),
                         deposit.paid_coin_amount)

    @patch('transactions.deposits.BlockChain')
    def test_insufficient_funds(self, bc_cls_mock):
        deposit = DepositFactory(
            merchant_coin_amount=Decimal('0.1'),
            fee_coin_amount=Decimal('0.01'))
        transactions = [Mock()]
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_tx_outputs.return_value': [{
                'address': deposit.deposit_address.address,
                'amount': Decimal('0.05'),
            }],
        })

        with self.assertRaises(InsufficientFunds):
            validate_payment(deposit, transactions)
        self.assertEqual(bc_mock.sign_raw_transaction.call_count, 1)
        deposit.refresh_from_db()
        self.assertEqual(deposit.paid_coin_amount, Decimal('0.05'))
        self.assertEqual(get_account_balance(deposit.account),
                         deposit.paid_coin_amount - deposit.fee_coin_amount)
        self.assertEqual(get_address_balance(deposit.deposit_address),
                         deposit.paid_coin_amount)


class WaitForPaymentTestCase(TestCase):

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    def test_payment_already_validated(self, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            time_received=timezone.now(),
            incoming_tx_ids=['0' * 64])
        wait_for_payment(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(bc_cls_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    def test_payment_cancelled(self, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(time_cancelled=timezone.now())
        wait_for_payment(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(bc_cls_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.validate_payment')
    def test_no_transactions(self, validate_mock, bc_cls_mock, cancel_mock):
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_unspent_transactions.return_value': [],
        })
        deposit = DepositFactory()
        wait_for_payment(deposit.pk)
        self.assertEqual(bc_mock.get_unspent_transactions.call_count, 1)
        self.assertIs(validate_mock.called, False)
        self.assertIs(cancel_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.get_txid')
    @patch('transactions.deposits.validate_payment')
    @patch('transactions.deposits.run_periodic_task')
    def test_validate_payment(self, run_task_mock, validate_mock,
                              get_txid_mock, bc_cls_mock, cancel_mock):
        customer_address = 'a' * 32
        incoming_tx = Mock()
        incoming_tx_id = '1' * 64
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_unspent_transactions.return_value': [incoming_tx],
            'get_tx_inputs.return_value': [{'address': customer_address}],
        })
        get_txid_mock.return_value = incoming_tx_id
        deposit = DepositFactory()
        wait_for_payment(deposit.pk)

        self.assertEqual(bc_mock.get_unspent_transactions.call_count, 1)
        self.assertEqual(bc_mock.get_unspent_transactions.call_args[0][0],
                         deposit.deposit_address.address)
        self.assertEqual(validate_mock.call_count, 1)
        self.assertEqual(validate_mock.call_args[0][0], deposit)
        self.assertEqual(validate_mock.call_args[0][1], [incoming_tx])
        self.assertIs(cancel_mock.called, True)
        self.assertIs(run_task_mock.called, True)
        self.assertEqual(run_task_mock.call_args[0][0].__name__,
                         'wait_for_confidence')
        self.assertEqual(run_task_mock.call_args[0][1], [deposit.pk])

        deposit.refresh_from_db()
        self.assertEqual(deposit.refund_address, customer_address)
        self.assertEqual(deposit.incoming_tx_ids, [incoming_tx_id])
        self.assertEqual(deposit.payment_type, PAYMENT_TYPES.BIP21)
        self.assertEqual(deposit.status, 'received')

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.get_txid')
    @patch('transactions.deposits.validate_payment')
    @patch('transactions.deposits.run_periodic_task')
    def test_mutilple_tx(self, run_task_mock, validate_mock, get_txid_mock,
                         bc_cls_mock, cancel_mock):
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.return_value': [Mock(), Mock()],
            'get_tx_inputs.return_value': [{'address': 'test_address'}],
        })
        incoming_tx_id_1 = '1' * 64
        incoming_tx_id_2 = '2' * 64
        get_txid_mock.side_effect = [incoming_tx_id_1, incoming_tx_id_2]
        deposit = DepositFactory()
        wait_for_payment(deposit.pk)

        self.assertEqual(validate_mock.call_count, 1)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(run_task_mock.called, True)
        deposit.refresh_from_db()
        self.assertEqual(deposit.incoming_tx_ids,
                         [incoming_tx_id_1, incoming_tx_id_2])

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.get_txid')
    @patch('transactions.deposits.validate_payment')
    def test_insufficient_funds(self, validate_mock, get_txid_mock,
                                bc_cls_mock, cancel_mock):
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.return_value': [Mock()],
            'get_tx_inputs.return_value': [{'address': 'test_address'}],
        })
        incoming_tx_id = '1' * 64
        get_txid_mock.return_value = incoming_tx_id

        def validate(deposit, _):
            deposit.paid_coin_amount = Decimal('0.001')
            deposit.save()
            raise InsufficientFunds

        validate_mock.side_effect = validate
        deposit = DepositFactory(amount=Decimal('10.00'),
                                 exchange_rate=Decimal('1000.00'))
        wait_for_payment(deposit.pk)

        self.assertIs(cancel_mock.called, False)
        deposit.refresh_from_db()
        self.assertEqual(deposit.incoming_tx_ids, [incoming_tx_id])
        self.assertEqual(deposit.status, 'underpaid')

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.get_txid')
    @patch('transactions.deposits.validate_payment')
    def test_validation_error(self, validate_mock, get_txid_mock,
                              bc_cls_mock, cancel_mock):
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.return_value': [Mock()],
            'get_tx_inputs.return_value': [{'address': 'test_address'}],
        })
        incoming_tx_id = '1' * 64
        get_txid_mock.return_value = incoming_tx_id
        validate_mock.side_effect = ValueError
        deposit = DepositFactory()
        wait_for_payment(deposit.pk)

        self.assertIs(cancel_mock.called, True)
        deposit.refresh_from_db()
        self.assertEqual(deposit.incoming_tx_ids, [incoming_tx_id])
        self.assertEqual(deposit.status, 'new')

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.get_txid')
    @patch('transactions.deposits.validate_payment')
    @patch('transactions.deposits.run_periodic_task')
    def test_repeat(self, run_task_mock, validate_mock, get_txid_mock,
                    bc_cls_mock, cancel_mock):
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.side_effect': [
                ['test_tx_1'],
                ['test_tx_1', 'test_tx_2'],
            ],
            'get_tx_inputs.return_value': [{'address': 'test_address'}],
        })
        incoming_tx_id_1 = '1' * 64
        incoming_tx_id_2 = '2' * 64
        get_txid_mock.side_effect = [
            incoming_tx_id_1,
            incoming_tx_id_1,
            incoming_tx_id_2,
        ]
        validate_mock.side_effect = [InsufficientFunds, None]
        deposit = DepositFactory()
        wait_for_payment(deposit.pk)
        wait_for_payment(deposit.pk)

        deposit.refresh_from_db()
        self.assertEqual(deposit.incoming_tx_ids,
                         [incoming_tx_id_1, incoming_tx_id_2])
        self.assertEqual(deposit.status, 'received')


class WaitForConfidenceTestCase(TestCase):

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    def test_already_broadcasted(self, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            time_received=timezone.now(),
            time_broadcasted=timezone.now())
        wait_for_confidence(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(bc_cls_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.is_tx_reliable')
    def test_tx_not_reliable(self, is_reliable_mock, bc_cls_mock,
                             cancel_mock):
        deposit = DepositFactory(
            time_received=timezone.now(),
            incoming_tx_ids=['0' * 64])
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.return_value': False,
        })
        is_reliable_mock.return_value = False
        wait_for_confidence(deposit.pk)

        self.assertIs(cancel_mock.called, False)
        self.assertEqual(bc_mock.is_tx_confirmed.call_count, 1)
        self.assertEqual(is_reliable_mock.call_count, 1)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.is_tx_reliable')
    def test_multiple_tx_not_reliable(self, is_reliable_mock,
                                      bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            time_received=timezone.now(),
            incoming_tx_ids=['0' * 64, '1' * 64])
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.side_effect': [False, False],
        })
        is_reliable_mock.side_effect = [False, False]
        wait_for_confidence(deposit.pk)

        self.assertIs(cancel_mock.called, False)
        self.assertEqual(bc_mock.is_tx_confirmed.call_count, 1)
        self.assertEqual(is_reliable_mock.call_count, 1)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.is_tx_reliable')
    def test_double_spend(self, is_reliable_mock,
                          bc_cls_mock, cancel_mock):
        incoming_tx_id = '0' * 64
        deposit = DepositFactory(
            time_received=timezone.now(),
            incoming_tx_ids=[incoming_tx_id])
        bc_cls_mock.return_value = Mock(**{
            'is_tx_confirmed.side_effect': DoubleSpend('1' * 64),
        })
        wait_for_confidence(deposit.pk)

        self.assertIs(is_reliable_mock.called, False)
        self.assertIs(cancel_mock.called, True)
        deposit.refresh_from_db()
        self.assertEqual(deposit.incoming_tx_ids, [incoming_tx_id])

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.is_tx_reliable')
    def test_tx_modified(self, is_reliable_mock,
                         bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            time_received=timezone.now(),
            incoming_tx_ids=['0' * 64])
        final_tx_id = 'e' * 64
        bc_cls_mock.return_value = Mock(**{
            'is_tx_confirmed.side_effect': TransactionModified(final_tx_id),
        })
        wait_for_confidence(deposit.pk)

        self.assertIs(is_reliable_mock.called, False)
        self.assertIs(cancel_mock.called, False)
        deposit.refresh_from_db()
        self.assertEqual(deposit.incoming_tx_ids, [final_tx_id])
        self.assertIsNone(deposit.time_broadcasted)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.is_tx_reliable')
    @patch('transactions.deposits.run_periodic_task')
    def test_broadcasted(self, run_task_mock, is_reliable_mock,
                         bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            time_received=timezone.now(),
            incoming_tx_ids=['0' * 64])
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.return_value': False,
        })
        is_reliable_mock.return_value = True
        wait_for_confidence(deposit.pk)

        self.assertIs(bc_mock.is_tx_confirmed.called, True)
        self.assertIs(is_reliable_mock.called, True)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(run_task_mock.called, True)
        self.assertEqual(run_task_mock.call_args[0][0].__name__,
                         'wait_for_confirmation')
        self.assertEqual(run_task_mock.call_args[0][1], [deposit.pk])
        deposit.refresh_from_db()
        self.assertIsNotNone(deposit.time_broadcasted)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.is_tx_reliable')
    @patch('transactions.deposits.run_periodic_task')
    def test_confirmed(self, run_task_mock, is_reliable_mock,
                       bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            time_received=timezone.now(),
            incoming_tx_ids=['0' * 64])
        bc_cls_mock.return_value = Mock(**{
            'is_tx_confirmed.return_value': True,
        })
        wait_for_confidence(deposit.pk)

        self.assertIs(is_reliable_mock.called, False)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(run_task_mock.called, True)
        deposit.refresh_from_db()
        self.assertIsNotNone(deposit.time_broadcasted)


class WaitForConfirmationTestCase(TestCase):

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    def test_confirmed(self, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            time_received=timezone.now(),
            time_broadcasted=timezone.now(),
            incoming_tx_ids=['0' * 64, '1' * 64])
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.side_effect': [True, True],
        })
        wait_for_confirmation(deposit.pk)
        self.assertEqual(bc_mock.is_tx_confirmed.call_count, 2)
        self.assertIs(cancel_mock.called, True)
        deposit.refresh_from_db()
        self.assertIsNotNone(deposit.time_confirmed)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    def test_not_confirmed(self, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            time_received=timezone.now(),
            time_broadcasted=timezone.now(),
            incoming_tx_ids=['a' * 64])
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.side_effect': [False, False],
        })
        wait_for_confirmation(deposit.pk)
        self.assertEqual(bc_mock.is_tx_confirmed.call_count, 1)
        self.assertIs(cancel_mock.called, False)
        deposit.refresh_from_db()
        self.assertIsNone(deposit.time_confirmed)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    def test_tx_modified(self, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            time_received=timezone.now(),
            time_broadcasted=timezone.now(),
            incoming_tx_ids=['a' * 64, 'b' * 64])
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.side_effect': TransactionModified('c' * 64),
        })
        wait_for_confirmation(deposit.pk)
        self.assertEqual(bc_mock.is_tx_confirmed.call_count, 1)
        self.assertIs(cancel_mock.called, False)
        deposit.refresh_from_db()
        self.assertEqual(deposit.incoming_tx_ids, ['c' * 64, 'b' * 64])
        self.assertIsNone(deposit.time_confirmed)


class RefundDepositTestCase(TestCase):

    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.create_tx_')
    def test_refund(self, create_tx_mock, bc_cls_mock):
        deposit = DepositFactory(
            received=True,
            amount=Decimal('10.00'),
            exchange_rate=Decimal('1000.00'))
        deposit.create_balance_changes()
        refund_tx_id = '5' * 64
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_raw_unspent_outputs.return_value': [{
                'txid': '1' * 64,
                'amount': Decimal('0.01'),
            }],
            'get_tx_fee.return_value': Decimal('0.0005'),
            'send_raw_transaction.return_value': refund_tx_id,
        })
        create_tx_mock.return_value = tx_mock = Mock()
        refund_deposit(deposit)

        deposit.refresh_from_db()
        self.assertEqual(deposit.refund_tx_id, refund_tx_id)
        self.assertEqual(deposit.status, 'refunded')
        self.assertEqual(deposit.balancechange_set.count(), 0)
        self.assertEqual(bc_mock.get_raw_unspent_outputs.call_count, 1)
        self.assertEqual(bc_mock.get_raw_unspent_outputs.call_args[0][0],
                         deposit.deposit_address.address)
        self.assertEqual(bc_mock.get_tx_fee.call_args[0], (1, 1))
        tx_inputs = create_tx_mock.call_args[0][0]
        self.assertEqual(len(tx_inputs), 1)
        self.assertIn('txid', tx_inputs[0])
        self.assertIn('private_key', tx_inputs[0])
        tx_outputs = create_tx_mock.call_args[0][1]
        self.assertEqual(len(tx_outputs.keys()), 1)
        self.assertEqual(tx_outputs[deposit.refund_address],
                         Decimal('0.0095'))
        self.assertEqual(bc_mock.send_raw_transaction.call_args[0][0],
                         tx_mock)

    def test_already_notified(self):
        deposit = DepositFactory(
            time_received=timezone.now(),
            time_broadcasted=timezone.now(),
            time_notified=timezone.now())
        with self.assertRaises(RefundError) as context:
            refund_deposit(deposit)
        self.assertEqual(context.exception.message,
                         'User already notified')

    def test_already_refunded(self):
        deposit = DepositFactory(time_refunded=timezone.now())
        with self.assertRaises(RefundError) as context:
            refund_deposit(deposit)
        self.assertEqual(context.exception.message,
                         'Deposit already refunded')

    def test_no_refund_address(self):
        deposit = DepositFactory(
            refund_address=None,
            time_cancelled=timezone.now())
        with self.assertRaises(RefundError) as context:
            refund_deposit(deposit)
        self.assertEqual(context.exception.message,
                         'No refund address')

    @patch('transactions.deposits.BlockChain')
    def test_nothing_to_send(self, bc_cls_mock):
        deposit = DepositFactory(
            amount=Decimal('10.00'),
            exchange_rate=Decimal('1000.00'),
            refund_address='1KYwqZshnYNUNweXrDkCAdLaixxPhePRje')
        bc_cls_mock.return_value = Mock(**{
            'get_raw_unspent_outputs.return_value': [],
            'get_tx_fee.return_value': Decimal('0.0005'),
        })
        with self.assertRaises(RefundError) as context:
            refund_deposit(deposit)
        self.assertEqual(context.exception.message,
                         'Nothing to refund')

    @patch('transactions.deposits.BlockChain')
    def test_dust_output(self, bc_cls_mock):
        deposit = DepositFactory(
            amount=Decimal('0.50'),
            exchange_rate=Decimal('1000.00'),
            refund_address='1KYwqZshnYNUNweXrDkCAdLaixxPhePRje')
        bc_cls_mock.return_value = Mock(**{
            'get_raw_unspent_outputs.return_value': [{
                'txid': '1' * 64,
                'amount': Decimal('0.0005'),
            }],
            'get_tx_fee.return_value': Decimal('0.000499'),
        })
        with self.assertRaises(RefundError) as context:
            refund_deposit(deposit)
        self.assertEqual(context.exception.message,
                         'Output is below dust threshold')


class CheckDepositStatusTestCase(TestCase):

    @patch('transactions.deposits.cancel_current_task')
    def test_new(self, cancel_mock):
        deposit = DepositFactory()
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    def test_notified(self, cancel_mock):
        deposit = DepositFactory(
            time_notified=timezone.now())
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    def test_confirmed(self, cancel_mock):
        deposit = DepositFactory(
            time_notified=timezone.now(),
            time_confirmed=timezone.now())
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, True)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.refund_deposit')
    @patch('transactions.deposits.logger')
    def test_timeout(self, logger_mock, refund_mock, cancel_mock):
        deposit = DepositFactory(
            time_created=timezone.now() - datetime.timedelta(hours=1))
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(refund_mock.called, True)
        self.assertIs(logger_mock.error.called, False)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.refund_deposit')
    @patch('transactions.deposits.logger')
    def test_failed(self, logger_mock, refund_mock, cancel_mock):
        deposit = DepositFactory(
            time_created=timezone.now() - datetime.timedelta(hours=2),
            time_received=timezone.now() - datetime.timedelta(hours=1))
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(refund_mock.called, True)
        self.assertIs(logger_mock.error.called, True)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.refund_deposit')
    @patch('transactions.deposits.logger')
    def test_unconfirmed(self, logger_mock, refund_mock, cancel_mock):
        deposit = DepositFactory(
            time_created=timezone.now() - datetime.timedelta(hours=4),
            time_received=timezone.now() - datetime.timedelta(hours=3),
            time_broadcasted=timezone.now() - datetime.timedelta(hours=3),
            time_notified=timezone.now() - datetime.timedelta(hours=3))
        self.assertEqual(deposit.status, 'unconfirmed')
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(refund_mock.called, False)
        self.assertIs(logger_mock.error.called, True)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.refund_deposit')
    @patch('transactions.deposits.logger')
    def test_refunded(self, logger_mock, refund_mock, cancel_mock):
        deposit = DepositFactory(
            time_created=timezone.now(),
            time_received=timezone.now(),
            time_refunded=timezone.now())
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(refund_mock.called, False)
        self.assertIs(logger_mock.error.called, False)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.refund_deposit')
    @patch('transactions.deposits.logger')
    def test_cancelled(self, logger_mock, refund_mock, cancel_mock):
        deposit = DepositFactory(
            time_cancelled=timezone.now())
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(refund_mock.called, True)
        self.assertIs(logger_mock.error.called, False)

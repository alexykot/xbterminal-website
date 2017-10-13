from decimal import Decimal

from django.test import TestCase

from mock import patch, Mock

from transactions.constants import PAYMENT_TYPES
from transactions.exceptions import (
    DustOutput,
    InvalidTransaction,
    InsufficientFunds,
    InvalidPaymentMessage,
    DoubleSpend,
    TransactionModified,
    RefundError)
from transactions.deposits import (
    prepare_deposit,
    validate_payment,
    handle_bip70_payment,
    wait_for_payment,
    wait_for_confidence,
    wait_for_confirmation,
    refund_deposit,
    check_deposit_status,
    check_deposit_confirmation)
from transactions.tests.factories import DepositFactory
from transactions.utils.compat import get_account_balance, get_address_balance
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
        incoming_tx_id = '1' * 64
        incoming_tx = Mock(**{'id.return_value': incoming_tx_id})
        refund_address = 'a' * 32
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_valid.return_value': True,
            'get_tx_outputs.return_value': [{
                'address': deposit.deposit_address.address,
                'amount': deposit.coin_amount,
            }],
        })
        result = validate_payment(
            deposit, [incoming_tx], [refund_address],
            PAYMENT_TYPES.BIP70)

        self.assertIs(result, True)
        self.assertEqual(bc_mock.is_tx_valid.call_count, 1)
        self.assertEqual(bc_mock.send_raw_transaction.call_count, 1)
        self.assertEqual(bc_mock.send_raw_transaction.call_args[0][0],
                         incoming_tx)
        deposit.refresh_from_db()
        self.assertEqual(deposit.paid_coin_amount, deposit.coin_amount)
        self.assertEqual(deposit.refund_address, refund_address)
        self.assertEqual(deposit.incoming_tx_ids, [incoming_tx_id])
        self.assertEqual(deposit.payment_type, PAYMENT_TYPES.BIP70)
        self.assertEqual(deposit.status, 'received')
        self.assertEqual(get_account_balance(deposit.account),
                         deposit.paid_coin_amount - deposit.fee_coin_amount)
        self.assertEqual(get_account_balance(deposit.account,
                                             include_unconfirmed=False), 0)
        self.assertEqual(get_address_balance(deposit.deposit_address),
                         deposit.paid_coin_amount)
        self.assertEqual(get_address_balance(deposit.deposit_address,
                                             include_unconfirmed=False), 0)

    @patch('transactions.deposits.BlockChain')
    def test_validate_multiple_tx(self, bc_cls_mock):
        deposit = DepositFactory(
            merchant_coin_amount=Decimal('0.1'),
            fee_coin_amount=Decimal('0.01'))
        self.assertEqual(deposit.status, 'new')
        incoming_tx_1 = Mock(**{'id.return_value': '1' * 64})
        incoming_tx_2 = Mock(**{'id.return_value': '2' * 64})
        refund_address = 'b' * 32
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_valid.return_value': True,
            'get_tx_outputs.side_effect': [
                [{
                    'address': deposit.deposit_address.address,
                    'amount': Decimal('0.05'),
                }],
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

        result_1 = validate_payment(
            deposit, [incoming_tx_1], [refund_address],
            PAYMENT_TYPES.BIP21)
        self.assertIs(result_1, False)
        self.assertEqual(bc_mock.is_tx_valid.call_count, 1)
        self.assertEqual(bc_mock.send_raw_transaction.call_count, 1)
        deposit.refresh_from_db()
        self.assertEqual(deposit.paid_coin_amount, Decimal('0.05'))
        self.assertEqual(deposit.incoming_tx_ids, ['1' * 64])
        self.assertIsNone(deposit.payment_type)
        self.assertEqual(deposit.status, 'underpaid')
        self.assertEqual(get_account_balance(deposit.account),
                         deposit.paid_coin_amount - deposit.fee_coin_amount)
        self.assertEqual(get_address_balance(deposit.deposit_address),
                         deposit.paid_coin_amount)

        bc_mock.reset_mock()
        result_2 = validate_payment(
            deposit, [incoming_tx_1, incoming_tx_2], [refund_address],
            PAYMENT_TYPES.BIP21)
        self.assertIs(result_2, True)
        self.assertEqual(bc_mock.is_tx_valid.call_count, 2)
        self.assertEqual(bc_mock.send_raw_transaction.call_count, 2)
        deposit.refresh_from_db()
        self.assertEqual(deposit.paid_coin_amount, Decimal('0.15'))
        self.assertEqual(deposit.incoming_tx_ids,
                         ['1' * 64, '2' * 64])
        self.assertEqual(deposit.payment_type, PAYMENT_TYPES.BIP21)
        self.assertEqual(deposit.status, 'received')
        self.assertEqual(get_account_balance(deposit.account),
                         deposit.paid_coin_amount - deposit.fee_coin_amount)
        self.assertEqual(get_address_balance(deposit.deposit_address),
                         deposit.paid_coin_amount)

    @patch('transactions.deposits.BlockChain')
    def test_no_refund_address(self, bc_cls_mock):
        deposit = DepositFactory()
        bc_cls_mock.return_value = Mock(**{
            'is_tx_valid.return_value': True,
            'get_tx_outputs.return_value': [{
                'address': deposit.deposit_address.address,
                'amount': deposit.coin_amount,
            }],
        })
        incoming_tx = Mock(**{'id.return_value': '1' * 64})
        validate_payment(deposit, [incoming_tx], [], PAYMENT_TYPES.BIP21)

        deposit.refresh_from_db()
        self.assertIsNone(deposit.refund_address)

    @patch('transactions.deposits.BlockChain')
    def test_underpaid_bip70(self, bc_cls_mock):
        deposit = DepositFactory(
            merchant_coin_amount=Decimal('0.1'),
            fee_coin_amount=Decimal('0.01'))
        incoming_tx = Mock(**{'id.return_value': '1' * 64})
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_valid.return_value': True,
            'get_tx_outputs.return_value': [{
                'address': deposit.deposit_address.address,
                'amount': Decimal('0.05'),
            }],
        })
        with self.assertRaises(InsufficientFunds):
            validate_payment(deposit, [incoming_tx], [],
                             PAYMENT_TYPES.BIP70)

        self.assertEqual(bc_mock.send_raw_transaction.call_count, 1)
        deposit.refresh_from_db()
        self.assertEqual(deposit.paid_coin_amount, 0)
        self.assertEqual(len(deposit.incoming_tx_ids), 0)
        self.assertEqual(deposit.status, 'new')

    @patch('transactions.deposits.BlockChain')
    def test_invalid_incoming_tx(self, bc_cls_mock):
        deposit = DepositFactory()
        incoming_tx_id = '1' * 64
        incoming_tx = Mock(**{'id.return_value': incoming_tx_id})
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_valid.return_value': False,
        })
        with self.assertRaises(InvalidTransaction) as context:
            validate_payment(deposit, [incoming_tx], [],
                             PAYMENT_TYPES.BIP21)
        self.assertEqual(context.exception.tx_id, incoming_tx_id)
        self.assertIs(bc_mock.send_raw_transaction.called, False)

    @patch('transactions.deposits.BlockChain')
    def test_cancelled(self, bc_cls_mock):
        deposit = DepositFactory(cancelled=True)
        incoming_tx_id = '1' * 64
        incoming_tx = Mock(**{'id.return_value': incoming_tx_id})
        refund_address = 'a' * 32
        bc_cls_mock.return_value = Mock(**{
            'is_tx_valid.return_value': True,
            'get_tx_outputs.return_value': [{
                'address': deposit.deposit_address.address,
                'amount': deposit.coin_amount,
            }],
        })
        result = validate_payment(
            deposit, [incoming_tx], [refund_address],
            PAYMENT_TYPES.BIP70)

        self.assertIs(result, False)
        deposit.refresh_from_db()
        self.assertEqual(deposit.paid_coin_amount, deposit.coin_amount)
        self.assertEqual(deposit.refund_address, refund_address)
        self.assertEqual(deposit.incoming_tx_ids, [incoming_tx_id])
        self.assertIsNone(deposit.time_received)


class HandleBIP70PaymentTestCase(TestCase):

    @patch('transactions.deposits.parse_payment')
    @patch('transactions.deposits.validate_payment')
    @patch('transactions.deposits.run_periodic_task')
    def test_valid(self, run_task_mock, validate_mock, parse_mock):
        deposit = DepositFactory()
        parse_mock.return_value = (['test_tx'], ['test_address'], 'test_ack')
        validate_mock.return_value = True
        payment_ack = handle_bip70_payment(deposit, 'test_message')

        self.assertIs(parse_mock.called, True)
        self.assertEqual(parse_mock.call_args[0][0], deposit.coin.name)
        self.assertEqual(parse_mock.call_args[0][1], 'test_message')
        self.assertIs(validate_mock.called, True)
        self.assertEqual(validate_mock.call_args[0][1], ['test_tx'])
        self.assertEqual(validate_mock.call_args[0][2], ['test_address'])
        self.assertEqual(validate_mock.call_args[0][3], PAYMENT_TYPES.BIP70)
        self.assertEqual(run_task_mock.call_args[0][0].__name__,
                         'wait_for_confidence')
        self.assertEqual(run_task_mock.call_args[0][1], [deposit.pk])
        self.assertEqual(payment_ack, 'test_ack')

    @patch('transactions.deposits.parse_payment')
    @patch('transactions.deposits.validate_payment')
    @patch('transactions.deposits.run_periodic_task')
    def test_repeat(self, run_task_mock, validate_mock, parse_mock):
        deposit = DepositFactory()
        validate_mock.side_effect = [True, False]
        parse_mock.return_value = (['test_tx'], ['test_address'], 'test_ack')
        handle_bip70_payment(deposit, 'test_message_1')
        handle_bip70_payment(deposit, 'test_message_2')

        self.assertEqual(validate_mock.call_count, 2)
        self.assertEqual(run_task_mock.call_count, 1)

    @patch('transactions.deposits.parse_payment')
    @patch('transactions.deposits.validate_payment')
    def test_invalid_message(self, validate_mock, parse_mock):
        deposit = DepositFactory()
        parse_mock.side_effect = ValueError
        with self.assertRaises(InvalidPaymentMessage):
            handle_bip70_payment(deposit, 'test_message')

        self.assertIs(parse_mock.called, True)
        self.assertIs(validate_mock.called, False)

    @patch('transactions.deposits.parse_payment')
    @patch('transactions.deposits.validate_payment')
    @patch('transactions.deposits.run_periodic_task')
    def test_insufficient_funds(self, run_task_mock, validate_mock,
                                parse_mock):
        deposit = DepositFactory()
        parse_mock.return_value = (['test_tx'], ['test_address'], 'test_ack')
        validate_mock.side_effect = InsufficientFunds
        with self.assertRaises(InsufficientFunds):
            handle_bip70_payment(deposit, 'test_message')

        self.assertIs(run_task_mock.called, False)


class WaitForPaymentTestCase(TestCase):

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    def test_payment_already_validated(self, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(received=True)
        wait_for_payment(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(bc_cls_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.validate_payment')
    def test_cancelled(self, validate_mock, bc_cls_mock, cancel_mock):
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.return_value': [],
        })
        deposit = DepositFactory(cancelled=True)
        wait_for_payment(deposit.pk)
        self.assertIs(cancel_mock.called, True)

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
    @patch('transactions.deposits.validate_payment')
    def test_timeout(self, validate_mock, bc_cls_mock, cancel_mock):
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.return_value': [],
        })
        deposit = DepositFactory(timeout=True)
        wait_for_payment(deposit.pk)
        self.assertIs(cancel_mock.called, True)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.validate_payment')
    @patch('transactions.deposits.run_periodic_task')
    def test_validate_payment(self, run_task_mock, validate_mock,
                              bc_cls_mock, cancel_mock):
        customer_address = 'a' * 32
        incoming_tx = Mock()
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_unspent_transactions.return_value': [incoming_tx],
            'get_tx_inputs.return_value': [{'address': customer_address}],
        })
        validate_payment.return_value = True
        deposit = DepositFactory()
        wait_for_payment(deposit.pk)

        self.assertEqual(bc_mock.get_unspent_transactions.call_count, 1)
        self.assertEqual(bc_mock.get_unspent_transactions.call_args[0][0],
                         deposit.deposit_address.address)
        self.assertEqual(validate_mock.call_count, 1)
        self.assertEqual(validate_mock.call_args[0][0], deposit)
        self.assertEqual(validate_mock.call_args[0][1], [incoming_tx])
        self.assertEqual(validate_mock.call_args[0][2], [customer_address])
        self.assertEqual(validate_mock.call_args[0][3], PAYMENT_TYPES.BIP21)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(run_task_mock.called, True)
        self.assertEqual(run_task_mock.call_args[0][0].__name__,
                         'wait_for_confidence')
        self.assertEqual(run_task_mock.call_args[0][1], [deposit.pk])

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.validate_payment')
    @patch('transactions.deposits.run_periodic_task')
    def test_underpaid(self, run_task_mock, validate_mock,
                       bc_cls_mock, cancel_mock):
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.return_value': [Mock()],
            'get_tx_inputs.return_value': [{'address': 'test_address'}],
        })
        validate_mock.return_value = False
        deposit = DepositFactory(amount=Decimal('10.00'),
                                 exchange_rate=Decimal('1000.00'))
        wait_for_payment(deposit.pk)

        self.assertIs(cancel_mock.called, False)
        self.assertIs(run_task_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.validate_payment')
    @patch('transactions.deposits.run_periodic_task')
    def test_validation_error(self, run_task_mock, validate_mock,
                              bc_cls_mock, cancel_mock):
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.return_value': [Mock()],
            'get_tx_inputs.return_value': [{'address': 'test_address'}],
        })
        validate_mock.side_effect = ValueError
        deposit = DepositFactory()
        wait_for_payment(deposit.pk)

        self.assertIs(cancel_mock.called, True)
        self.assertIs(run_task_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.validate_payment')
    @patch('transactions.deposits.run_periodic_task')
    def test_repeat(self, run_task_mock, validate_mock,
                    bc_cls_mock, cancel_mock):
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.side_effect': [
                ['test_tx_1'],
                ['test_tx_1', 'test_tx_2'],
            ],
            'get_tx_inputs.return_value': [{'address': 'test_address'}],
        })
        validate_mock.side_effect = [False, True]
        deposit = DepositFactory()
        wait_for_payment(deposit.pk)
        wait_for_payment(deposit.pk)

        self.assertEqual(validate_mock.call_count, 2)
        self.assertEqual(run_task_mock.call_count, 1)
        self.assertEqual(cancel_mock.call_count, 1)


class WaitForConfidenceTestCase(TestCase):

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    def test_already_broadcasted(self, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(broadcasted=True)
        wait_for_confidence(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(bc_cls_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    def test_cancelled(self, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(cancelled=True)
        with self.assertRaises(AssertionError):
            wait_for_confidence(deposit.pk)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.is_tx_reliable')
    def test_tx_not_reliable(self, is_reliable_mock, bc_cls_mock,
                             cancel_mock):
        deposit = DepositFactory(received=True)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.return_value': False,
        })
        is_reliable_mock.return_value = False
        wait_for_confidence(deposit.pk)

        self.assertIs(cancel_mock.called, False)
        self.assertEqual(bc_mock.is_tx_confirmed.call_count, 1)
        self.assertEqual(is_reliable_mock.call_count, 1)
        self.assertEqual(is_reliable_mock.call_args[0][0],
                         deposit.incoming_tx_ids[0])
        self.assertEqual(is_reliable_mock.call_args[0][2],
                         deposit.coin.name)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.is_tx_reliable')
    def test_multiple_tx_not_reliable(self, is_reliable_mock,
                                      bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            received=True,
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
            received=True,
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
        deposit = DepositFactory(received=True)
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
    @patch('transactions.deposits.refund_deposit')
    @patch('transactions.deposits.run_periodic_task')
    def test_broadcasted(self, run_task_mock, refund_mock,
                         is_reliable_mock, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(received=True)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.return_value': False,
        })
        is_reliable_mock.return_value = True
        wait_for_confidence(deposit.pk)

        self.assertIs(bc_mock.is_tx_confirmed.called, True)
        self.assertIs(is_reliable_mock.called, True)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(refund_mock.called, False)
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
        deposit = DepositFactory(received=True)
        bc_cls_mock.return_value = Mock(**{
            'is_tx_confirmed.return_value': True,
        })
        wait_for_confidence(deposit.pk)

        self.assertIs(is_reliable_mock.called, False)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(run_task_mock.called, True)
        deposit.refresh_from_db()
        self.assertIsNotNone(deposit.time_broadcasted)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.is_tx_reliable')
    @patch('transactions.deposits.refund_deposit')
    @patch('transactions.deposits.run_periodic_task')
    def test_refund_extra(self, run_task_mock, refund_mock,
                          is_reliable_mock, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            received=True,
            merchant_coin_amount=Decimal('0.010'),
            fee_coin_amount=Decimal('0.001'),
            paid_coin_amount=Decimal('0.015'))
        bc_cls_mock.return_value = Mock(**{
            'is_tx_confirmed.return_value': False,
        })
        is_reliable_mock.return_value = True
        wait_for_confidence(deposit.pk)

        self.assertIs(cancel_mock.called, True)
        self.assertIs(refund_mock.called, True)
        self.assertIs(refund_mock.call_args[1]['only_extra'], True)
        self.assertIs(run_task_mock.called, True)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.is_tx_reliable')
    def test_timeout(self, is_reliable_mock, bc_cls_mock,
                     cancel_mock):
        deposit = DepositFactory(failed=True)
        bc_cls_mock.return_value = Mock(**{
            'is_tx_confirmed.return_value': False,
        })
        is_reliable_mock.return_value = False
        wait_for_confidence(deposit.pk)
        self.assertIs(cancel_mock.called, True)


class WaitForConfirmationTestCase(TestCase):

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    def test_confirmed(self, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            broadcasted=True,
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
        deposit = DepositFactory(broadcasted=True)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.return_value': False,
        })
        wait_for_confirmation(deposit.pk)
        self.assertEqual(bc_mock.is_tx_confirmed.call_count, 1)
        self.assertIs(cancel_mock.called, False)
        deposit.refresh_from_db()
        self.assertIsNone(deposit.time_confirmed)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    def test_timeout(self, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(unconfirmed=True)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.return_value': False,
        })
        wait_for_confirmation(deposit.pk)
        self.assertEqual(bc_mock.is_tx_confirmed.call_count, 1)
        self.assertIs(cancel_mock.called, True)
        deposit.refresh_from_db()
        self.assertIsNone(deposit.time_confirmed)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.BlockChain')
    def test_tx_modified(self, bc_cls_mock, cancel_mock):
        deposit = DepositFactory(
            broadcasted=True,
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
    @patch('transactions.deposits.create_tx')
    def test_refund(self, create_tx_mock, bc_cls_mock):
        deposit = DepositFactory(
            failed=True,
            amount=Decimal('10.00'),
            exchange_rate=Decimal('1000.00'),
            fee_coin_amount=0)
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
        self.assertEqual(deposit.refund_coin_amount, Decimal('0.01'))
        self.assertEqual(deposit.refund_tx_id, refund_tx_id)
        self.assertEqual(deposit.status, 'failed')
        self.assertEqual(deposit.balancechange_set.count(), 0)
        self.assertEqual(bc_mock.get_raw_unspent_outputs.call_count, 1)
        self.assertEqual(bc_mock.get_raw_unspent_outputs.call_args[0][0],
                         deposit.deposit_address.address)
        self.assertIs(bc_mock.get_raw_transaction.called, False)
        self.assertIs(bc_mock.get_tx_inputs.called, False)
        self.assertEqual(bc_mock.get_tx_fee.call_args[0], (1, 2))
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

    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.create_tx')
    def test_refund_only_extra(self, create_tx_mock, bc_cls_mock):
        deposit = DepositFactory(
            received=True,
            merchant_coin_amount=Decimal('0.010'),
            fee_coin_amount=Decimal('0.001'),
            paid_coin_amount=Decimal('0.015'))
        deposit.create_balance_changes()
        refund_tx_id = '5' * 64
        bc_cls_mock.return_value = Mock(**{
            'get_raw_unspent_outputs.return_value': [{
                'txid': '1' * 64,
                'amount': Decimal('0.015'),
            }],
            'get_tx_fee.return_value': Decimal('0.0005'),
            'send_raw_transaction.return_value': refund_tx_id,
        })
        refund_deposit(deposit, only_extra=True)

        deposit.refresh_from_db()
        self.assertEqual(deposit.refund_coin_amount, Decimal('0.004'))
        self.assertEqual(deposit.refund_tx_id, refund_tx_id)
        self.assertEqual(deposit.status, 'received')
        self.assertEqual(deposit.balancechange_set.count(), 3)
        tx_outputs = create_tx_mock.call_args[0][1]
        self.assertEqual(len(tx_outputs.keys()), 2)
        self.assertEqual(tx_outputs[deposit.refund_address],
                         Decimal('0.0035'))
        self.assertEqual(tx_outputs[deposit.deposit_address.address],
                         Decimal('0.011'))

    def test_already_notified(self):
        deposit = DepositFactory(notified=True)
        with self.assertRaises(RefundError) as context:
            refund_deposit(deposit)
        self.assertEqual(context.exception.message,
                         'User already notified')

    def test_cancelled_only_extra(self):
        deposit = DepositFactory(cancelled=True)
        with self.assertRaises(RefundError) as context:
            refund_deposit(deposit, only_extra=True)
        self.assertEqual(
            context.exception.message,
            'Partial refund is not possible for cancelled deposits')

    def test_already_refunded(self):
        deposit = DepositFactory(refunded=True)
        with self.assertRaises(RefundError) as context:
            refund_deposit(deposit)
        self.assertEqual(context.exception.message,
                         'Deposit already refunded')

    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.create_tx')
    def test_payment_not_processed(self, create_tx_mock, bc_cls_mock):
        deposit = DepositFactory(
            cancelled=True,
            timeout=True,
            refund_address=None)
        refund_address = 'a' * 32
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_raw_unspent_outputs.return_value': [{
                'txid': '9' * 64,
                'amount': Decimal('0.01'),
            }],
            'get_tx_inputs.return_value': [{
                'address': refund_address,
                'amount': Decimal('0.01'),
            }],
            'get_tx_fee.return_value': Decimal('0.0005'),
            'send_raw_transaction.return_value': '6' * 64,
        })
        refund_deposit(deposit)

        deposit.refresh_from_db()
        self.assertEqual(deposit.balancechange_set.count(), 0)
        self.assertEqual(bc_mock.get_raw_transaction.call_args[0][0],
                         '9' * 64)
        self.assertIs(bc_mock.get_tx_inputs.called, True)
        tx_outputs = create_tx_mock.call_args[0][1]
        self.assertEqual(len(tx_outputs.keys()), 1)
        self.assertEqual(tx_outputs[refund_address],
                         Decimal('0.0095'))

    @patch('transactions.deposits.BlockChain')
    def test_nothing_to_send(self, bc_cls_mock):
        deposit = DepositFactory(
            failed=True,
            amount=Decimal('10.00'),
            exchange_rate=Decimal('1000.00'))
        bc_cls_mock.return_value = Mock(**{
            'get_raw_unspent_outputs.return_value': [],
            'get_tx_fee.return_value': Decimal('0.0005'),
        })
        with self.assertRaises(RefundError) as context:
            refund_deposit(deposit)
        self.assertEqual(context.exception.message,
                         'Nothing to refund')

    @patch('transactions.deposits.BlockChain')
    @patch('transactions.deposits.create_tx')
    def test_dust_output(self, create_tx_mock, bc_cls_mock):
        deposit = DepositFactory(
            failed=True,
            amount=Decimal('0.50'),
            exchange_rate=Decimal('1000.00'))
        bc_cls_mock.return_value = Mock(**{
            'get_raw_unspent_outputs.return_value': [{
                'txid': '1' * 64,
                'amount': Decimal('0.0005'),
            }],
            'get_tx_fee.return_value': Decimal('0.000499'),
        })
        create_tx_mock.side_effect = DustOutput
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
        deposit = DepositFactory(notified=True)
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    def test_confirmed(self, cancel_mock):
        deposit = DepositFactory(confirmed=True)
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, True)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.refund_deposit')
    def test_timeout(self, refund_mock, cancel_mock):
        deposit = DepositFactory(timeout=True)
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(refund_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.refund_deposit')
    @patch('transactions.deposits.logger')
    def test_failed(self, logger_mock, refund_mock, cancel_mock):
        deposit = DepositFactory(failed=True)
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(refund_mock.called, True)
        self.assertIs(logger_mock.error.called, True)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.refund_deposit')
    @patch('transactions.deposits.logger')
    def test_unconfirmed(self, logger_mock, refund_mock, cancel_mock):
        deposit = DepositFactory(unconfirmed=True)
        self.assertEqual(deposit.status, 'unconfirmed')
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(refund_mock.called, False)
        self.assertIs(logger_mock.error.called, True)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.refund_deposit')
    def test_cancelled(self, refund_mock, cancel_mock):
        deposit = DepositFactory(cancelled=True)
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, False)
        self.assertIs(refund_mock.called, False)

    @patch('transactions.deposits.cancel_current_task')
    @patch('transactions.deposits.refund_deposit')
    @patch('transactions.deposits.logger')
    def test_cancelled_timeout(self, logger_mock, refund_mock, cancel_mock):
        deposit = DepositFactory(cancelled=True, timeout=True)
        refund_mock.side_effect = RefundError('Nothing to refund')
        check_deposit_status(deposit.pk)
        self.assertIs(cancel_mock.called, True)
        self.assertIs(refund_mock.called, True)
        self.assertIs(logger_mock.exception.called, False)


class CheckDepositConfirmationTestCase(TestCase):

    def test_already_confirmed(self):
        deposit = DepositFactory(confirmed=True)
        result = check_deposit_confirmation(deposit)
        self.assertIs(result, True)

    @patch('transactions.deposits.BlockChain')
    def test_confirmed(self, bc_cls_mock):
        deposit = DepositFactory(
            incoming_tx_ids=['1' * 64, '2' * 64],
            notified=True)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.side_effect': [True, True],
        })
        result = check_deposit_confirmation(deposit)

        self.assertIs(result, True)
        self.assertEqual(bc_mock.is_tx_confirmed.call_count, 2)
        deposit.refresh_from_db()
        self.assertIsNotNone(deposit.time_confirmed)

    @patch('transactions.deposits.BlockChain')
    def test_not_confirmed(self, bc_cls_mock):
        deposit = DepositFactory(
            incoming_tx_ids=['1' * 64, '2' * 64],
            notified=True)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.side_effect': [False, True],
        })
        result = check_deposit_confirmation(deposit)

        self.assertIs(result, False)
        self.assertEqual(bc_mock.is_tx_confirmed.call_count, 1)
        deposit.refresh_from_db()
        self.assertIsNone(deposit.time_confirmed)

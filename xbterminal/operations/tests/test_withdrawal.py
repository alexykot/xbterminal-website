import datetime
from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.utils import timezone
from mock import patch, Mock

from bitcoin.core import COutPoint

from website.tests.factories import (
    DeviceFactory,
    AccountFactory,
    AddressFactory)
from operations.tests.factories import (
    WithdrawalOrderFactory,
    outpoint_factory)
from operations import withdrawal, exceptions


class PrepareWithdrawalTestCase(TestCase):

    @patch('operations.withdrawal.BlockChain')
    @patch('operations.withdrawal.get_exchange_rate')
    def test_prepare_btc(self, get_rate_mock, bc_cls_mock):
        account_address = AddressFactory.create()
        device = DeviceFactory.create(account=account_address.account)
        fiat_amount = Decimal('1.00')
        exchange_rate = Decimal(100)
        get_rate_mock.return_value = exchange_rate
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_unspent_outputs.return_value': [
                {'amount': Decimal('0.005'), 'outpoint': outpoint_factory()},
                {'amount': Decimal('0.007'), 'outpoint': outpoint_factory()},
            ],
        })

        order = withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(order.device.pk, device.pk)
        self.assertEqual(order.account.pk, device.account.pk)
        self.assertEqual(order.bitcoin_network, device.bitcoin_network)
        self.assertIsNone(order.merchant_address)
        self.assertEqual(order.fiat_currency.pk,
                         device.merchant.currency.pk)
        self.assertEqual(order.fiat_amount, fiat_amount)
        self.assertEqual(order.exchange_rate, exchange_rate)
        self.assertEqual(order.customer_btc_amount, Decimal('0.01'))
        self.assertEqual(order.tx_fee_btc_amount, Decimal('0.0001'))
        self.assertEqual(order.change_btc_amount, Decimal('0.0019'))
        self.assertIsNotNone(order.reserved_outputs)
        self.assertEqual(order.status, 'new')
        self.assertEqual(bc_mock.get_unspent_outputs.call_count, 1)
        self.assertEqual(
            bc_mock.get_unspent_outputs.call_args[0][0],
            account_address.address)
        self.assertEqual(
            bc_mock.get_unspent_outputs.call_args[1]['minconf'], 1)

    @patch('operations.withdrawal.BlockChain')
    @patch('operations.withdrawal.get_exchange_rate')
    def test_prepare_btc_multiple_addresses(self, get_rate_mock, bc_cls_mock):
        account = AccountFactory.create()
        address_1, address_2 = AddressFactory.create_batch(
            2, account=account)
        device = DeviceFactory.create(account=account)
        fiat_amount = Decimal('9.00')
        get_rate_mock.return_value = Decimal(100)
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_unspent_outputs.side_effect': [
                [
                    {'amount': Decimal('0.05'), 'outpoint': outpoint_factory()},
                ],
                [
                    {'amount': Decimal('0.05'), 'outpoint': outpoint_factory()},
                    {'amount': Decimal('0.03'), 'outpoint': outpoint_factory()},
                ],
            ],
        })

        order = withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(order.account.pk, account.pk)
        self.assertEqual(order.customer_btc_amount, Decimal('0.09'))
        self.assertEqual(order.tx_fee_btc_amount, Decimal('0.0001'))
        self.assertEqual(order.change_btc_amount, Decimal('0.0099'))
        self.assertEqual(bc_mock.get_unspent_outputs.call_count, 2)
        self.assertEqual(bc_mock.get_unspent_outputs.call_args_list[0][0][0],
                         address_2.address)
        self.assertEqual(bc_mock.get_unspent_outputs.call_args_list[1][0][0],
                         address_1.address)

    def test_no_account(self):
        device = DeviceFactory.create(status='registered')
        fiat_amount = Decimal('1.00')
        with self.assertRaises(exceptions.WithdrawalError) as context:
            withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(context.exception.message,
                         'Account is not set for device.')

    def test_currency_mismatch(self):
        device = DeviceFactory.create(
            merchant__currency__name='GBP',
            account__currency__name='USD')
        fiat_amount = Decimal('1.5')
        with self.assertRaises(exceptions.WithdrawalError) as context:
            withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(context.exception.message,
                         'Account currency should match merchant currency.')

    def test_no_address(self):
        device = DeviceFactory.create()
        fiat_amount = Decimal('1.00')
        with self.assertRaises(exceptions.WithdrawalError) as context:
            withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(context.exception.message,
                         'Nothing to withdraw.')

    @patch('operations.withdrawal.get_exchange_rate')
    def test_dust_threshold(self, get_rate_mock):
        account_address = AddressFactory.create()
        device = DeviceFactory.create(account=account_address.account)
        fiat_amount = Decimal('0.05')
        get_rate_mock.return_value = Decimal(1000)
        with self.assertRaises(exceptions.WithdrawalError):
            withdrawal.prepare_withdrawal(device, fiat_amount)

    @patch('operations.withdrawal.BlockChain')
    @patch('operations.withdrawal.get_exchange_rate')
    def test_insufficient_funds_btc(self, get_rate_mock, bc_mock):
        account_address = AddressFactory.create()
        device = DeviceFactory.create(account=account_address.account)
        fiat_amount = Decimal('200.00')
        get_rate_mock.return_value = Decimal(200)
        bc_mock.return_value = Mock(**{
            'get_unspent_outputs.return_value':
                [{'amount': Decimal('0.9'), 'outpoint': outpoint_factory()}],
        })

        with self.assertRaises(exceptions.WithdrawalError) as context:
            withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(context.exception.message, 'Insufficient funds.')

    @patch('operations.withdrawal.BlockChain')
    @patch('operations.withdrawal.get_exchange_rate')
    def test_already_reserved(self, get_rate_mock, bc_mock):
        account_address = AddressFactory.create()
        device = DeviceFactory.create(account=account_address.account)
        reserved_output = outpoint_factory()
        order = WithdrawalOrderFactory.create(
            device=device,
            merchant_address=account_address.address,
            reserved_outputs=[reserved_output])

        fiat_amount = Decimal('200.00')
        get_rate_mock.return_value = Decimal(200)
        bc_mock.return_value = Mock(**{
            'get_unspent_outputs.return_value': [
                {'amount': Decimal('1.5'), 'outpoint': reserved_output},
            ],
        })
        with self.assertRaises(exceptions.WithdrawalError) as context:
            withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(context.exception.message, 'Insufficient funds.')

        # Order cancelled
        order.time_cancelled = timezone.now()
        order.save()

        new_order = withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(order.reserved_outputs,
                         new_order.reserved_outputs)

    @patch('operations.withdrawal.BlockChain')
    @patch('operations.withdrawal.get_exchange_rate')
    def test_dust_change(self, get_rate_mock, bc_mock):
        account_address = AddressFactory.create()
        device = DeviceFactory.create(account=account_address.account)
        fiat_amount = Decimal('1.00')
        exchange_rate = Decimal(200)
        get_rate_mock.return_value = exchange_rate
        bc_mock.return_value = Mock(**{
            'get_unspent_outputs.return_value': [
                {'amount': Decimal('0.005105'), 'outpoint': outpoint_factory()},
            ],
        })

        order = withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(order.customer_btc_amount, Decimal('0.005005'))
        self.assertEqual(order.tx_fee_btc_amount, Decimal('0.0001'))
        self.assertEqual(order.change_btc_amount, Decimal(0))

    @patch('operations.withdrawal.get_exchange_rate')
    def test_prepare_instantfiat(self, get_rate_mock):
        device = DeviceFactory.create(
            account__currency__name='GBP',
            account__balance=Decimal('2.00'))
        self.assertTrue(device.account.instantfiat)
        self.assertEqual(device.account.balance_confirmed, Decimal('2.00'))
        fiat_amount = Decimal('1.00')
        get_rate_mock.return_value = exchange_rate = Decimal(100)

        order = withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(order.device.pk, device.pk)
        self.assertEqual(order.bitcoin_network, 'mainnet')
        self.assertIsNone(order.merchant_address)
        self.assertEqual(order.fiat_currency.pk,
                         device.merchant.currency.pk)
        self.assertEqual(order.fiat_amount, fiat_amount)
        self.assertEqual(order.exchange_rate, exchange_rate)
        self.assertEqual(order.customer_btc_amount, Decimal('0.01'))
        self.assertEqual(order.tx_fee_btc_amount, 0)
        self.assertEqual(order.change_btc_amount, 0)
        self.assertEqual(order.btc_amount, Decimal('0.01'))
        self.assertEqual(order.reserved_outputs, '')
        self.assertEqual(order.status, 'new')

    @patch('operations.withdrawal.get_exchange_rate')
    def test_insufficient_funds_instantfiat(self, get_rate_mock):
        device = DeviceFactory.create(account__currency__name='GBP')
        self.assertEqual(device.account.balance_confirmed, 0)
        fiat_amount = Decimal('200.00')
        get_rate_mock.return_value = Decimal(200)
        with self.assertRaises(exceptions.WithdrawalError) as context:
            withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(context.exception.message, 'Insufficient funds.')

    @patch('operations.withdrawal.BlockChain')
    @patch('operations.withdrawal.get_exchange_rate')
    def test_prepare_no_device(self, get_rate_mock, bc_cls_mock):
        account = AccountFactory.create()
        AddressFactory.create(account=account)
        fiat_amount = Decimal('1.00')
        get_rate_mock.return_value = Decimal(100)
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_outputs.return_value': [
                {'amount': Decimal('0.1'), 'outpoint': outpoint_factory()},
            ],
        })

        order = withdrawal.prepare_withdrawal(account, fiat_amount)
        self.assertIsNone(order.device)
        self.assertEqual(order.account.pk, account.pk)
        self.assertEqual(order.fiat_currency.pk,
                         account.merchant.currency.pk)


class SendTransactionTestCase(TestCase):

    @patch('operations.withdrawal.BlockChain')
    @patch('operations.withdrawal.run_periodic_task')
    def test_send_btc(self, run_task_mock, bc_cls_mock):
        account = AccountFactory(balance=Decimal('0.01'))
        account_address = AddressFactory.create(account=account)
        device = DeviceFactory.create(account=account)
        incoming_tx_hash = b'\x01' * 32
        order = WithdrawalOrderFactory.create(
            device=device,
            fiat_amount=Decimal('1.00'),
            tx_fee_btc_amount=Decimal('0.0001'),
            change_btc_amount=Decimal('0.0049'),
            reserved_outputs=[COutPoint(hash=incoming_tx_hash)],
            exchange_rate=Decimal(200))
        customer_address = '1NdS5JCXzbhNv4STQAaknq56iGstfgRCXg'
        outgoing_tx_id = '0' * 64
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'create_raw_transaction.return_value': 'test_tx',
            'sign_raw_transaction.return_value': 'test_tx_signed',
            'send_raw_transaction.return_value': outgoing_tx_id,
        })

        withdrawal.send_transaction(order, customer_address)
        order.refresh_from_db()
        self.assertEqual(order.customer_address, customer_address)
        self.assertEqual(order.btc_amount, Decimal('0.0051'))
        self.assertEqual(order.change_btc_amount, Decimal('0.0049'))
        self.assertEqual(order.outgoing_tx_id, outgoing_tx_id)
        self.assertEqual(order.status, 'sent')

        self.assertTrue(run_task_mock.called)
        self.assertEqual(run_task_mock.call_args[0][0].__name__,
                         'wait_for_confidence')

        inputs, outputs = bc_mock.create_raw_transaction.call_args[0]
        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0].hash, incoming_tx_hash)
        self.assertEqual(len(outputs.keys()), 2)
        self.assertEqual(outputs[order.customer_address],
                         order.customer_btc_amount)
        self.assertEqual(outputs[account_address.address],
                         order.change_btc_amount)

        self.assertEqual(order.transaction_set.count(), 2)
        account_tx_1 = order.transaction_set.get(amount__lt=0)
        self.assertEqual(account_tx_1.amount,
                         -(order.btc_amount + order.change_btc_amount))
        account_tx_2 = order.transaction_set.get(amount__gt=0)
        self.assertEqual(account_tx_2.amount,
                         order.change_btc_amount)

        self.assertEqual(device.account.balance, Decimal('0.0049'))

    @patch('operations.withdrawal.BlockChain')
    @patch('operations.withdrawal.run_periodic_task')
    def test_send_btc_without_change(self, run_task_mock, bc_cls_mock):
        account = AccountFactory.create(balance=Decimal('0.0051'))
        account_address = AddressFactory.create(account=account)
        device = DeviceFactory.create(account=account)
        order = WithdrawalOrderFactory.create(
            device=device,
            fiat_amount=Decimal('1.00'),
            tx_fee_btc_amount=Decimal('0.0001'),
            reserved_outputs=[COutPoint()],
            exchange_rate=Decimal(200))
        customer_address = '1NdS5JCXzbhNv4STQAaknq56iGstfgRCXg'
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'create_raw_transaction.return_value': 'test_tx',
            'sign_raw_transaction.return_value': 'test_tx_signed',
            'send_raw_transaction.return_value': '0' * 64,
        })

        withdrawal.send_transaction(order, customer_address)
        order.refresh_from_db()
        self.assertEqual(order.change_btc_amount, 0)
        self.assertEqual(order.status, 'sent')
        self.assertEqual(order.transaction_set.count(), 1)
        account_tx_1 = order.transaction_set.get(amount__lt=0)
        self.assertEqual(account_tx_1.amount, -order.btc_amount)
        self.assertEqual(device.account.balance, 0)
        self.assertIn(account_address.address,
                      bc_mock.create_raw_transaction.call_args[0][1])

    def test_invalid_address(self):
        order = WithdrawalOrderFactory.create()
        customer_address = 'mhXPmYBSUsjEKmyi568cEoZYR3QHHkhMyG'
        with self.assertRaises(exceptions.WithdrawalError):
            withdrawal.send_transaction(order, customer_address)

    def test_outputs_already_reserved(self):
        account = AccountFactory.create()
        order_1, order_2 = WithdrawalOrderFactory.create_batch(
            2,
            device__account=account,
            reserved_outputs=[outpoint_factory()])
        customer_address = '1NdS5JCXzbhNv4STQAaknq56iGstfgRCXg'

        with self.assertRaises(exceptions.WithdrawalError) as context:
            withdrawal.send_transaction(order_2, customer_address)
        self.assertEqual(context.exception.message, 'Insufficient funds.')

    @patch('operations.withdrawal.instantfiat.send_transaction')
    @patch('operations.withdrawal.run_periodic_task')
    def test_send_instantfiat(self, run_task_mock, send_mock):
        device = DeviceFactory.create(
            account__currency__name='GBP',
            account__balance=Decimal('2.00'))
        self.assertTrue(device.account.instantfiat)
        order = WithdrawalOrderFactory.create(
            device=device,
            fiat_amount=Decimal('1.00'),
            tx_fee_btc_amount=0,
            change_btc_amount=0,
            exchange_rate=Decimal(200))
        customer_address = '1NdS5JCXzbhNv4STQAaknq56iGstfgRCXg'
        send_mock.return_value = ('test-id', 'test-ref', Decimal('0.006'))

        withdrawal.send_transaction(order, customer_address)
        order.refresh_from_db()
        self.assertTrue(send_mock.called)
        self.assertEqual(send_mock.call_args[0][1], order.fiat_amount)
        self.assertEqual(send_mock.call_args[0][2], customer_address)
        self.assertEqual(order.customer_address, customer_address)
        self.assertEqual(order.customer_btc_amount, Decimal('0.006'))
        self.assertIsNone(order.outgoing_tx_id)
        self.assertEqual(order.instantfiat_transfer_id, 'test-id')
        self.assertEqual(order.instantfiat_reference, 'test-ref')
        self.assertEqual(order.status, 'new')

        self.assertEqual(order.transaction_set.count(), 1)
        account_tx = order.transaction_set.get(amount__lt=0)
        self.assertEqual(account_tx.amount, -order.fiat_amount)
        self.assertEqual(device.account.balance, Decimal('1.00'))

        self.assertTrue(run_task_mock.called)
        self.assertEqual(run_task_mock.call_args[0][0].__name__,
                         'wait_for_processor')

    @patch('operations.withdrawal.instantfiat.send_transaction')
    def test_send_instantfiat_insufficient_funds(self, send_mock):
        device = DeviceFactory.create(
            account__currency__name='GBP',
            account__balance=Decimal('2.00'))
        order = WithdrawalOrderFactory.create(
            device=device,
            fiat_amount=Decimal('1.00'),
            tx_fee_btc_amount=0,
            change_btc_amount=0,
            exchange_rate=Decimal(200))
        customer_address = '1NdS5JCXzbhNv4STQAaknq56iGstfgRCXg'
        send_mock.side_effect = exceptions.InsufficientFunds

        with self.assertRaises(exceptions.WithdrawalError) as context:
            withdrawal.send_transaction(order, customer_address)
        self.assertEqual(context.exception.message, 'Insufficient funds.')

    @patch('operations.withdrawal.instantfiat.send_transaction')
    def test_send_instantfiat_error(self, send_mock):
        device = DeviceFactory.create(
            account__currency__name='GBP',
            account__balance=Decimal('2.00'))
        order = WithdrawalOrderFactory.create(
            device=device,
            fiat_amount=Decimal('1.00'),
            tx_fee_btc_amount=0,
            change_btc_amount=0,
            exchange_rate=Decimal(200))
        customer_address = '1NdS5JCXzbhNv4STQAaknq56iGstfgRCXg'
        send_mock.side_effect = ValueError

        with self.assertRaises(exceptions.WithdrawalError) as context:
            withdrawal.send_transaction(order, customer_address)
        self.assertEqual(context.exception.message, 'Instantfiat error.')


class WaitForConfidenceTestCase(TestCase):

    @patch('operations.withdrawal.cancel_current_task')
    @patch('operations.withdrawal.is_tx_reliable')
    def test_tx_broadcasted(self, tx_check_mock, cancel_mock):
        order = WithdrawalOrderFactory.create(
            time_sent=timezone.now())
        tx_check_mock.return_value = True
        withdrawal.wait_for_confidence(order.uid)
        order.refresh_from_db()
        self.assertEqual(order.status, 'broadcasted')
        self.assertTrue(cancel_mock.called)

    @patch('operations.withdrawal.cancel_current_task')
    @patch('operations.withdrawal.is_tx_reliable')
    def test_tx_not_broadcasted(self, tx_check_mock, cancel_mock):
        order = WithdrawalOrderFactory.create(
            time_sent=timezone.now())
        tx_check_mock.return_value = False
        withdrawal.wait_for_confidence(order.uid)
        order.refresh_from_db()
        self.assertEqual(order.status, 'sent')
        self.assertFalse(cancel_mock.called)

    @patch('operations.withdrawal.cancel_current_task')
    @patch('operations.withdrawal.is_tx_reliable')
    def test_does_not_exist(self, tx_check_mock, cancel_mock):
        withdrawal.wait_for_confidence('invalid_uid')
        self.assertTrue(cancel_mock.called)
        self.assertFalse(tx_check_mock.called)

    @patch('operations.withdrawal.cancel_current_task')
    @patch('operations.withdrawal.send_error_message')
    @patch('operations.withdrawal.is_tx_reliable')
    def test_timeout(self, tx_check_mock, send_mock, cancel_mock):
        order = WithdrawalOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=1),
            time_sent=timezone.now() - datetime.timedelta(hours=1))
        withdrawal.wait_for_confidence(order.uid)
        order.refresh_from_db()
        self.assertEqual(order.status, 'failed')
        self.assertTrue(cancel_mock.called)
        self.assertTrue(send_mock.called)
        self.assertEqual(send_mock.call_args[1]['order'].pk, order.pk)
        self.assertFalse(tx_check_mock.called)


class WaitForProcessorTestCase(TestCase):

    @patch('operations.withdrawal.cancel_current_task')
    @patch('operations.withdrawal.instantfiat.check_transfer')
    def test_completed(self, check_mock, cancel_mock):
        order = WithdrawalOrderFactory.create()
        tx_id = '4' * 64
        check_mock.return_value = (True, tx_id)
        withdrawal.wait_for_processor(order.uid)
        self.assertTrue(check_mock.called)
        self.assertEqual(check_mock.call_args[0][0],
                         order.device.account)
        self.assertEqual(check_mock.call_args[0][1],
                         order.instantfiat_transfer_id)
        order.refresh_from_db()
        self.assertEqual(order.status, 'broadcasted')
        self.assertEqual(order.outgoing_tx_id, tx_id)
        self.assertTrue(cancel_mock.called)

    @patch('operations.withdrawal.cancel_current_task')
    @patch('operations.withdrawal.instantfiat.check_transfer')
    def test_not_completed(self, check_mock, cancel_mock):
        order = WithdrawalOrderFactory.create()
        check_mock.return_value = (False, None)
        withdrawal.wait_for_processor(order.uid)
        order.refresh_from_db()
        self.assertEqual(order.status, 'new')
        self.assertIsNone(order.outgoing_tx_id)
        self.assertFalse(cancel_mock.called)

    @patch('operations.withdrawal.cancel_current_task')
    @patch('operations.withdrawal.instantfiat.check_transfer')
    def test_error(self, check_mock, cancel_mock):
        order = WithdrawalOrderFactory.create()
        check_mock.side_effect = ValueError
        withdrawal.wait_for_processor(order.uid)
        order.refresh_from_db()
        self.assertEqual(order.status, 'new')
        self.assertIsNone(order.outgoing_tx_id)
        self.assertFalse(cancel_mock.called)

    @patch('operations.withdrawal.cancel_current_task')
    @patch('operations.withdrawal.instantfiat.check_transfer')
    def test_timeout(self, check_mock, cancel_mock):
        order = WithdrawalOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=1))
        withdrawal.wait_for_processor(order.uid)
        order.refresh_from_db()
        self.assertEqual(order.status, 'timeout')
        self.assertTrue(cancel_mock.called)
        self.assertFalse(check_mock.called)
        self.assertEqual(len(mail.outbox), 1)

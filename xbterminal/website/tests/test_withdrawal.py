from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from mock import patch, Mock

from bitcoin.core import COutPoint

from website.models import WithdrawalOrder
from website.tests.factories import (
    BTCAccountFactory,
    DeviceFactory,
    WithdrawalOrderFactory)
from operations import withdrawal


class PrepareWithdrawalTestCase(TestCase):

    fixtures = ['initial_data.json']

    @patch('operations.withdrawal.BlockChain')
    @patch('operations.withdrawal.get_exchange_rate')
    def test_prepare(self, get_rate_mock, bc_mock):
        device = DeviceFactory.create()
        btc_account = BTCAccountFactory.create(
            merchant=device.merchant,
            address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        fiat_amount = Decimal('1.00')
        exchange_rate = Decimal(200)
        get_rate_mock.return_value = exchange_rate
        bc_mock.return_value = Mock(**{
            'get_unspent_outputs.return_value': [
                {'amount': Decimal('0.1'), 'outpoint': COutPoint(n=1)},
            ],
        })

        order = withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(order.device.pk, device.pk)
        self.assertEqual(order.bitcoin_network, device.bitcoin_network)
        self.assertEqual(order.merchant_address, btc_account.address)
        self.assertEqual(order.fiat_currency.pk,
                         device.merchant.currency.pk)
        self.assertEqual(order.fiat_amount, fiat_amount)
        self.assertEqual(order.exchange_rate, exchange_rate)
        self.assertEqual(order.customer_btc_amount, Decimal('0.005'))
        self.assertEqual(order.tx_fee_btc_amount, Decimal('0.0001'))
        self.assertEqual(order.change_btc_amount, Decimal('0.0949'))
        self.assertIsNotNone(order.reserved_outputs)
        self.assertEqual(order.status, 'new')

    def test_no_account(self):
        device = DeviceFactory.create()
        fiat_amount = Decimal('1.00')
        with self.assertRaises(withdrawal.WithdrawalError):
            withdrawal.prepare_withdrawal(device, fiat_amount)

    def test_no_address(self):
        device = DeviceFactory.create()
        btc_account = BTCAccountFactory.create(merchant=device.merchant)
        fiat_amount = Decimal('1.00')
        with self.assertRaises(withdrawal.WithdrawalError):
            withdrawal.prepare_withdrawal(device, fiat_amount)

    @patch('operations.withdrawal.get_exchange_rate')
    def test_dust_threshold(self, get_rate_mock):
        device = DeviceFactory.create()
        btc_account = BTCAccountFactory.create(
            merchant=device.merchant,
            address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        fiat_amount = Decimal('0.05')
        get_rate_mock.return_value = Decimal(1000)
        with self.assertRaises(withdrawal.WithdrawalError):
            withdrawal.prepare_withdrawal(device, fiat_amount)

    @patch('operations.withdrawal.BlockChain')
    @patch('operations.withdrawal.get_exchange_rate')
    def test_insufficient_funds(self, get_rate_mock, bc_mock):
        device = DeviceFactory.create()
        btc_account = BTCAccountFactory.create(
            merchant=device.merchant,
            address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        fiat_amount = Decimal('200.00')
        get_rate_mock.return_value = Decimal(200)
        bc_mock.return_value = Mock(**{
            'get_unspent_outputs.return_value':
                [{'amount': Decimal('0.9'), 'outpoint': COutPoint(n=1)}],
        })

        with self.assertRaises(withdrawal.WithdrawalError):
            withdrawal.prepare_withdrawal(device, fiat_amount)

    @patch('operations.withdrawal.BlockChain')
    @patch('operations.withdrawal.get_exchange_rate')
    def test_dust_change(self, get_rate_mock, bc_mock):
        device = DeviceFactory.create()
        btc_account = BTCAccountFactory.create(
            merchant=device.merchant,
            address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        fiat_amount = Decimal('1.00')
        exchange_rate = Decimal(200)
        get_rate_mock.return_value = exchange_rate
        bc_mock.return_value = Mock(**{
            'get_unspent_outputs.return_value': [
                {'amount': Decimal('0.005105'), 'outpoint': COutPoint(n=1)},
            ],
        })

        order = withdrawal.prepare_withdrawal(device, fiat_amount)
        self.assertEqual(order.customer_btc_amount, Decimal('0.005005'))
        self.assertEqual(order.tx_fee_btc_amount, Decimal('0.0001'))
        self.assertEqual(order.change_btc_amount, Decimal(0))


class SendTransactionTestCase(TestCase):

    fixtures = ['initial_data.json']

    @patch('operations.withdrawal.BlockChain')
    @patch('operations.withdrawal.run_periodic_task')
    def test_send_tx(self, run_task_mock, bc_mock):
        device = DeviceFactory.create()
        btc_account = BTCAccountFactory.create(
            merchant=device.merchant,
            balance=Decimal('0.01'),
            address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
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
        bc_instance_mock = Mock(**{
            'create_raw_transaction.return_value': 'test_tx',
            'sign_raw_transaction.return_value': 'test_tx_signed',
            'send_raw_transaction.return_value': outgoing_tx_id,
        })
        bc_mock.return_value = bc_instance_mock

        withdrawal.send_transaction(order, customer_address)
        order = WithdrawalOrder.objects.get(pk=order.pk)
        self.assertEqual(order.customer_address, customer_address)
        self.assertEqual(order.btc_amount, Decimal('0.0051'))
        self.assertEqual(order.outgoing_tx_id, outgoing_tx_id)
        self.assertEqual(order.status, 'sent')

        self.assertTrue(run_task_mock.called)

        inputs, outputs = bc_instance_mock.create_raw_transaction.call_args[0]
        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0].hash, incoming_tx_hash)
        self.assertEqual(len(outputs.keys()), 2)
        self.assertEqual(outputs[order.customer_address],
                         order.customer_btc_amount)
        self.assertEqual(outputs[order.merchant_address],
                         Decimal('0.0049'))

        self.assertEqual(device.merchant.get_account_balance('mainnet'),
                         Decimal('0.0049'))

    def test_invalid_address(self):
        order = WithdrawalOrderFactory.create()
        customer_address = 'mhXPmYBSUsjEKmyi568cEoZYR3QHHkhMyG'
        with self.assertRaises(withdrawal.WithdrawalError):
            withdrawal.send_transaction(order, customer_address)


class WaitForBroadcastTestCase(TestCase):

    fixtures = ['initial_data.json']

    @patch('operations.withdrawal.cancel_current_task')
    @patch('operations.withdrawal.blockr.is_tx_broadcasted')
    def test_task(self, bcast_mock, cancel_mock):
        order = WithdrawalOrderFactory.create(
            time_sent=timezone.now())
        bcast_mock.return_value = True
        withdrawal.wait_for_broadcast(order.uid)
        order = WithdrawalOrder.objects.get(pk=order.pk)
        self.assertEqual(order.status, 'broadcasted')
        self.assertTrue(cancel_mock.called)

    @patch('operations.withdrawal.cancel_current_task')
    @patch('operations.withdrawal.blockr.is_tx_broadcasted')
    def test_does_not_exist(self, bcast_mock, cancel_mock):
        withdrawal.wait_for_broadcast('invalid_uid')
        self.assertTrue(cancel_mock.called)
        self.assertFalse(bcast_mock.called)

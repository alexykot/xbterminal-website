from decimal import Decimal
import datetime
from django.test import TestCase
from django.utils import timezone
from mock import patch, Mock

from constance import config

from website.models import Account
from website.tests.factories import (
    MerchantAccountFactory,
    AccountFactory,
    DeviceFactory)
from operations.models import PaymentOrder
from operations.tests.factories import PaymentOrderFactory
from operations import payment, exceptions
from operations import BTC_DEC_PLACES


class PreparePaymentTestCase(TestCase):

    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.get_exchange_rate')
    @patch('operations.payment.run_periodic_task')
    def test_keep_btc(self, run_task_mock, get_rate_mock, bc_mock):
        device = DeviceFactory.create(
            percent=0,
            bitcoin_address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        AccountFactory.create(merchant=device.merchant)
        fiat_amount = Decimal('10')
        exchange_rate = Decimal('235.64')
        local_address = '1KYwqZshnYNUNweXrDkCAdLaixxPhePRje'

        bc_mock.return_value = Mock(**{
            'get_new_address.return_value': local_address,
        })
        get_rate_mock.return_value = exchange_rate

        payment_order = payment.prepare_payment(device, fiat_amount)
        expected_fee_btc_amount = (fiat_amount *
                                   Decimal(config.OUR_FEE_SHARE) /
                                   exchange_rate).quantize(BTC_DEC_PLACES)
        expected_merchant_btc_amount = (fiat_amount /
                                        exchange_rate).quantize(BTC_DEC_PLACES)
        expected_btc_amount = (expected_merchant_btc_amount +
                               expected_fee_btc_amount +
                               Decimal('0.0001'))

        self.assertEqual(payment_order.local_address,
                         local_address)
        self.assertEqual(payment_order.merchant_address,
                         device.bitcoin_address)
        self.assertEqual(payment_order.fee_address,
                         config.OUR_FEE_MAINNET_ADDRESS)
        self.assertIsNone(payment_order.instantfiat_address)
        self.assertEqual(payment_order.fiat_currency.pk,
                         device.merchant.currency.pk)
        self.assertEqual(payment_order.fiat_amount, fiat_amount)
        self.assertEqual(payment_order.instantfiat_fiat_amount, 0)
        self.assertEqual(payment_order.instantfiat_btc_amount, 0)
        self.assertEqual(payment_order.merchant_btc_amount,
                         expected_merchant_btc_amount)
        self.assertEqual(payment_order.fee_btc_amount,
                         expected_fee_btc_amount)
        self.assertEqual(payment_order.tx_fee_btc_amount,
                         Decimal('0.0001'))
        self.assertEqual(payment_order.btc_amount,
                         expected_btc_amount)
        self.assertIsNone(payment_order.instantfiat_invoice_id)
        self.assertEqual(len(payment_order.incoming_tx_ids), 0)
        self.assertIsNone(payment_order.outgoing_tx_id)
        self.assertEqual(payment_order.status, 'new')

        calls = run_task_mock.call_args_list
        self.assertEqual(calls[0][0][0].__name__, 'wait_for_payment')
        self.assertEqual(calls[1][0][0].__name__, 'wait_for_validation')
        self.assertEqual(calls[2][0][0].__name__, 'check_payment_status')

    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.get_exchange_rate')
    @patch('operations.payment.run_periodic_task')
    def test_keep_btc_without_fee(self, run_task_mock, get_rate_mock, bc_mock):
        device = DeviceFactory.create(
            device_type='hardware',
            percent=0,
            bitcoin_address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        AccountFactory.create(merchant=device.merchant)
        fiat_amount = Decimal('1')
        exchange_rate = Decimal('235.64')
        local_address = '1KYwqZshnYNUNweXrDkCAdLaixxPhePRje'

        bc_mock.return_value = Mock(**{
            'get_new_address.return_value': local_address,
        })
        get_rate_mock.return_value = exchange_rate

        payment_order = payment.prepare_payment(device, fiat_amount)
        expected_merchant_btc_amount = (fiat_amount /
                                        exchange_rate).quantize(BTC_DEC_PLACES)
        expected_btc_amount = (expected_merchant_btc_amount +
                               Decimal('0.0001'))

        self.assertEqual(payment_order.fiat_amount, fiat_amount)
        self.assertEqual(payment_order.instantfiat_fiat_amount, 0)
        self.assertEqual(payment_order.instantfiat_btc_amount, 0)
        self.assertEqual(payment_order.merchant_btc_amount,
                         expected_merchant_btc_amount)
        self.assertEqual(payment_order.fee_btc_amount, 0)
        self.assertEqual(payment_order.btc_amount,
                         expected_btc_amount)

    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.instantfiat.create_invoice')
    @patch('operations.payment.run_periodic_task')
    def test_convert_full(self, run_task_mock, invoice_mock, bc_mock):
        device = DeviceFactory.create(percent=100, bitcoin_address='')
        AccountFactory.create(merchant=device.merchant)
        fiat_amount = Decimal('10')
        local_address = '1KYwqZshnYNUNweXrDkCAdLaixxPhePRje'
        instantfiat_invoice_id = 'test_invoice_123'
        instantfiat_btc_amount = Decimal('0.043')
        instantfiat_address = '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'

        bc_mock.return_value = Mock(**{
            'get_new_address.return_value': local_address,
        })
        invoice_mock.return_value = (
            instantfiat_invoice_id,
            instantfiat_btc_amount,
            instantfiat_address)

        payment_order = payment.prepare_payment(device, fiat_amount)
        expected_fee_btc_amount = (instantfiat_btc_amount *
                                   Decimal(config.OUR_FEE_SHARE)).quantize(BTC_DEC_PLACES)
        expected_btc_amount = (instantfiat_btc_amount +
                               expected_fee_btc_amount +
                               Decimal('0.0001'))

        self.assertEqual(payment_order.local_address,
                         local_address)
        self.assertEqual(payment_order.merchant_address, '')
        self.assertEqual(payment_order.instantfiat_address,
                         instantfiat_address)
        self.assertEqual(payment_order.fiat_amount,
                         fiat_amount)
        self.assertEqual(payment_order.instantfiat_fiat_amount,
                         fiat_amount)
        self.assertEqual(payment_order.instantfiat_btc_amount,
                         instantfiat_btc_amount)
        self.assertEqual(payment_order.merchant_btc_amount, 0)
        self.assertEqual(payment_order.fee_btc_amount,
                         expected_fee_btc_amount)
        self.assertEqual(payment_order.btc_amount,
                         expected_btc_amount)
        self.assertEqual(payment_order.instantfiat_invoice_id,
                         instantfiat_invoice_id)

    def test_no_btc_account(self):
        device = DeviceFactory.create(
            percent=0,
            bitcoin_address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        fiat_amount = Decimal('10')
        with self.assertRaises(exceptions.PaymentError) as context:
            payment.prepare_payment(device, fiat_amount)
        self.assertEqual(context.exception.message,
                         'Merchant doesn\'t have BTC account')


class WaitForPaymentTestCase(TestCase):

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockchain.BlockChain')
    def test_payment_order_does_not_exist(self, bc_mock, cancel_mock):
        payment.wait_for_payment(123456)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(bc_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockchain.BlockChain')
    def test_payment_already_validated(self, bc_mock, cancel_mock):
        payment_order = PaymentOrderFactory.create(
            time_recieved=timezone.now(),
            incoming_tx_ids=['0' * 64])
        payment.wait_for_payment(payment_order.uid)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(bc_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockchain.BlockChain')
    def test_payment_cancelled(self, bc_cls_mock, cancel_mock):
        order = PaymentOrderFactory.create(
            time_cancelled=timezone.now())
        payment.wait_for_payment(order.uid)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(bc_cls_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.validate_payment')
    def test_no_transactions(self, validate_mock, bc_mock, cancel_mock):
        bc_instance_mock = Mock(**{
            'get_unspent_transactions.return_value': [],
        })
        bc_mock.return_value = bc_instance_mock

        payment_order = PaymentOrderFactory.create()
        payment.wait_for_payment(payment_order.uid)
        self.assertFalse(cancel_mock.called)
        self.assertTrue(bc_instance_mock.get_unspent_transactions.called)
        self.assertFalse(validate_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.validate_payment')
    @patch('operations.payment.blockchain.get_txid')
    def test_validate_payment(self, get_txid_mock, validate_mock,
                              bc_mock, cancel_mock):
        customer_address = 'a' * 32
        bc_mock.return_value = bc_instance_mock = Mock(**{
            'get_unspent_transactions.return_value': ['test_tx'],
            'get_tx_inputs.return_value': [{'address': customer_address}],
        })
        incoming_tx_id = '1' * 64
        get_txid_mock.return_value = incoming_tx_id

        order = PaymentOrderFactory.create()
        payment.wait_for_payment(order.uid)

        self.assertTrue(bc_instance_mock.get_unspent_transactions.called)
        args = bc_instance_mock.get_unspent_transactions.call_args[0]
        self.assertEqual(str(args[0]), order.local_address)

        self.assertTrue(validate_mock.called)
        args = validate_mock.call_args[0]
        self.assertEqual(args[0].uid, order.uid)
        self.assertEqual(args[1], ['test_tx'])
        self.assertTrue(cancel_mock.called)

        order.refresh_from_db()
        self.assertEqual(order.refund_address, customer_address)
        self.assertEqual(order.incoming_tx_ids[0], incoming_tx_id)
        self.assertEqual(order.payment_type, 'bip0021')
        self.assertEqual(order.status, 'recieved')

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.validate_payment')
    @patch('operations.payment.blockchain.get_txid')
    def test_mutilple_tx(self, get_txid_mock, validate_mock,
                         bc_cls_mock, cancel_mock):
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.return_value': ['test_tx_1', 'test_tx_2'],
            'get_tx_inputs.return_value': [{'address': 'test_address'}],
        })
        incoming_tx_id_1 = '1' * 64
        incoming_tx_id_2 = '2' * 64
        get_txid_mock.side_effect = [incoming_tx_id_1, incoming_tx_id_2]

        order = PaymentOrderFactory.create()
        payment.wait_for_payment(order.uid)

        self.assertEqual(validate_mock.call_count, 1)
        self.assertTrue(cancel_mock.called)
        order.refresh_from_db()
        self.assertIn(incoming_tx_id_1, order.incoming_tx_ids)
        self.assertIn(incoming_tx_id_2, order.incoming_tx_ids)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.validate_payment')
    @patch('operations.payment.reverse_payment')
    @patch('operations.payment.blockchain.get_txid')
    def test_insufficient_funds(self, get_txid_mock, reverse_mock,
                                validate_mock, bc_cls_mock, cancel_mock):
        customer_address = 'a' * 32
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.return_value': ['test_tx'],
            'get_tx_inputs.return_value': [{'address': customer_address}],
        })
        validate_mock.side_effect = exceptions.InsufficientFunds
        incoming_tx_id = '1' * 64
        get_txid_mock.return_value = incoming_tx_id

        order = PaymentOrderFactory.create()
        payment.wait_for_payment(order.uid)
        self.assertTrue(validate_mock.called)
        self.assertFalse(reverse_mock.called)
        self.assertFalse(cancel_mock.called)
        order.refresh_from_db()
        self.assertEqual(order.incoming_tx_ids[0], incoming_tx_id)
        self.assertEqual(order.refund_address, customer_address)
        self.assertIsNone(order.time_recieved)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.validate_payment')
    @patch('operations.payment.reverse_payment')
    @patch('operations.payment.blockchain.get_txid')
    def test_validation_error(self, get_txid_mock, reverse_mock,
                              validate_mock, bc_cls_mock, cancel_mock):
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.return_value': ['test_tx'],
            'get_tx_inputs.return_value': [{'address': 'test_address'}],
        })
        validate_mock.side_effect = ValueError
        incoming_tx_id = '1' * 64
        get_txid_mock.return_value = incoming_tx_id

        order = PaymentOrderFactory.create()
        payment.wait_for_payment(order.uid)
        self.assertFalse(reverse_mock.called)
        self.assertTrue(cancel_mock.called)
        order.refresh_from_db()
        self.assertEqual(order.incoming_tx_ids[0], incoming_tx_id)
        self.assertIsNone(order.time_recieved)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.validate_payment')
    @patch('operations.payment.blockchain.get_txid')
    def test_repeat(self, get_txid_mock, validate_mock,
                    bc_cls_mock, cancel_mock):
        customer_address = 'a' * 32
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_transactions.side_effect': [
                ['test_tx_1'],
                ['test_tx_1', 'test_tx_2'],
            ],
            'get_tx_inputs.return_value': [{'address': customer_address}],
        })
        validate_mock.side_effect = [exceptions.InsufficientFunds, None]
        incoming_tx_id_1 = '1' * 64
        incoming_tx_id_2 = '2' * 64
        get_txid_mock.side_effect = [
            incoming_tx_id_1,
            incoming_tx_id_1,
            incoming_tx_id_2,
        ]

        order = PaymentOrderFactory.create()
        payment.wait_for_payment(order.uid)
        payment.wait_for_payment(order.uid)

        order.refresh_from_db()
        self.assertEqual(len(order.incoming_tx_ids), 2)
        self.assertIn(incoming_tx_id_1, order.incoming_tx_ids)
        self.assertIn(incoming_tx_id_2, order.incoming_tx_ids)


class ParsePaymentTestCase(TestCase):

    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.protocol.parse_payment')
    @patch('operations.payment.validate_payment')
    @patch('operations.payment.blockchain.get_txid')
    def test_valid(self, get_txid_mock, validate_mock,
                   parse_mock, bc_cls_mock):
        order = PaymentOrderFactory.create()
        bc_cls_mock.return_value = bc_mock = Mock()
        parse_mock.return_value = (['test_tx'], ['test_address'], 'test_ack')
        incoming_tx_id = '1' * 64
        get_txid_mock.return_value = incoming_tx_id
        result = payment.parse_payment(order, 'test_message')
        self.assertTrue(parse_mock.called)
        self.assertTrue(validate_mock.called)
        self.assertEqual(validate_mock.call_args[0][1][0], 'test_tx')
        self.assertEqual(bc_mock.sign_raw_transaction.call_count, 1)
        self.assertEqual(bc_mock.send_raw_transaction.call_count, 1)
        self.assertEqual(result, 'test_ack')
        order.refresh_from_db()
        self.assertEqual(order.refund_address, 'test_address')
        self.assertEqual(order.incoming_tx_ids[0], incoming_tx_id)
        self.assertEqual(order.payment_type, 'bip0070')
        self.assertEqual(order.status, 'recieved')

    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.protocol.parse_payment')
    @patch('operations.payment.validate_payment')
    @patch('operations.payment.blockchain.get_txid')
    def test_multiple_tx(self, get_txid_mock, validate_mock,
                         parse_mock, bc_cls_mock):
        order = PaymentOrderFactory.create()
        bc_cls_mock.return_value = bc_mock = Mock()
        parse_mock.return_value = (
            ['test_tx_1', 'test_tx_2'],
            ['test_address_1', 'test_address_2'],
            'test_ack')
        incoming_tx_id_1 = '1' * 64
        incoming_tx_id_2 = '2' * 64
        get_txid_mock.side_effect = [incoming_tx_id_1, incoming_tx_id_2]
        result = payment.parse_payment(order, 'test_message')
        self.assertIsNotNone(result)
        self.assertEqual(len(validate_mock.call_args[0][1]), 2)
        self.assertEqual(bc_mock.sign_raw_transaction.call_count, 2)
        self.assertEqual(bc_mock.send_raw_transaction.call_count, 2)
        order.refresh_from_db()
        self.assertEqual(order.refund_address, 'test_address_1')
        self.assertIn(incoming_tx_id_1, order.incoming_tx_ids)
        self.assertIn(incoming_tx_id_2, order.incoming_tx_ids)

    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.protocol.parse_payment')
    @patch('operations.payment.validate_payment')
    @patch('operations.payment.blockchain.get_txid')
    def test_repeat(self, get_txid_mock, validate_mock,
                    parse_mock, bc_cls_mock):
        order = PaymentOrderFactory.create()
        bc_cls_mock.return_value = bc_mock = Mock()
        parse_mock.return_value = (['test_tx'], ['test_address'], 'test_ack')
        incoming_tx_id = '1' * 64
        get_txid_mock.return_value = incoming_tx_id
        payment.parse_payment(order, 'test_message_1')
        payment.parse_payment(order, 'test_message_2')
        self.assertEqual(bc_mock.sign_raw_transaction.call_count, 2)
        self.assertEqual(bc_mock.send_raw_transaction.call_count, 2)
        order.refresh_from_db()
        self.assertEqual(len(order.incoming_tx_ids), 1)

    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.protocol.parse_payment')
    @patch('operations.payment.validate_payment')
    def test_invalid_message(self, validate_mock, parse_mock, bc_cls_mock):
        order = PaymentOrderFactory.create()
        parse_mock.side_effect = ValueError
        with self.assertRaises(exceptions.InvalidPaymentMessage):
            payment.parse_payment(order, 'test_message')
        self.assertTrue(parse_mock.called)
        self.assertFalse(validate_mock.called)
        order.refresh_from_db()
        self.assertEqual(len(order.incoming_tx_ids), 0)
        self.assertIsNone(order.time_recieved)

    @patch('operations.payment.blockchain.BlockChain')
    @patch('operations.payment.protocol.parse_payment')
    @patch('operations.payment.validate_payment')
    @patch('operations.payment.blockchain.get_txid')
    def test_insufficient_funds(self, get_txid_mock, validate_mock,
                                parse_mock, bc_cls_mock):
        order = PaymentOrderFactory.create()
        bc_cls_mock.return_value = bc_mock = Mock()
        parse_mock.return_value = (['test_tx'], ['test_address'], 'test_ack')
        incoming_tx_id = '1' * 64
        get_txid_mock.return_value = incoming_tx_id
        validate_mock.side_effect = exceptions.InsufficientFunds
        with self.assertRaises(exceptions.InsufficientFunds):
            payment.parse_payment(order, 'test_message')
        self.assertTrue(parse_mock.called)
        self.assertTrue(bc_mock.sign_raw_transaction.called)
        self.assertTrue(bc_mock.send_raw_transaction.called)
        self.assertTrue(validate_mock.called)
        order.refresh_from_db()
        self.assertEqual(order.incoming_tx_ids[0], incoming_tx_id)
        self.assertIsNone(order.time_recieved)


class ValidatePaymentTestCase(TestCase):

    @patch('operations.payment.blockchain.BlockChain')
    def test_validate(self, bc_cls_mock):
        order = PaymentOrderFactory.create()
        incoming_txs = [Mock()]
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'sign_raw_transaction.return_value': Mock(),
            'get_tx_outputs.return_value': [{
                'address': order.local_address,
                'amount': order.btc_amount,
            }],
        })

        payment.validate_payment(order, incoming_txs)
        self.assertTrue(bc_mock.sign_raw_transaction.called)
        order.refresh_from_db()
        self.assertEqual(len(order.incoming_tx_ids), 0)
        self.assertEqual(order.status, 'new')

    @patch('operations.payment.blockchain.BlockChain')
    def test_multiple_tx(self, bc_cls_mock):
        order = PaymentOrderFactory.create(
            merchant_btc_amount=Decimal('0.1'),
            btc_amount=Decimal('0.1001'))
        incoming_txs = [Mock(), Mock()]
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'sign_raw_transaction.return_value': Mock(),
            'get_tx_outputs.side_effect': [
                [{'address': order.local_address, 'amount': Decimal('0.5')}],
                [{'address': order.local_address, 'amount': Decimal('0.5001')}],
            ],
        })

        payment.validate_payment(order, incoming_txs)
        self.assertEqual(bc_mock.sign_raw_transaction.call_count, 2)
        order.refresh_from_db()
        self.assertEqual(len(order.incoming_tx_ids), 0)
        self.assertEqual(order.status, 'new')

    @patch('operations.payment.blockchain.BlockChain')
    def test_validation_error(self, bc_cls_mock):
        order = PaymentOrderFactory.create()
        incoming_tx = Mock()
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'sign_raw_transaction.side_effect': ValueError,
        })

        with self.assertRaises(ValueError):
            payment.validate_payment(order, [incoming_tx])
        self.assertTrue(bc_mock.sign_raw_transaction.called)

    @patch('operations.payment.blockchain.BlockChain')
    def test_insufficient_funds(self, bc_cls_mock):
        order = PaymentOrderFactory.create(
            merchant_btc_amount=Decimal('0.1'),
            btc_amount=Decimal('0.1001'))
        incoming_tx = Mock()
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'sign_raw_transaction.return_value': Mock(),
            'get_tx_outputs.return_value': [{
                'address': order.local_address,
                'amount': Decimal('0.05'),
            }],
        })

        with self.assertRaises(exceptions.InsufficientFunds):
            payment.validate_payment(order, [incoming_tx])
        self.assertTrue(bc_mock.sign_raw_transaction.called)


class ReversePaymentTestCase(TestCase):

    @patch('operations.payment.blockchain.BlockChain')
    def test_reverse(self, bc_cls_mock):
        order = PaymentOrderFactory.create(
            merchant_btc_amount=Decimal('0.1'),
            fee_btc_amount=Decimal('0.001'),
            btc_amount=Decimal('0.1011'),
            refund_address='1KYwqZshnYNUNweXrDkCAdLaixxPhePRje')
        refund_tx_id = '5' * 64
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'get_unspent_outputs.return_value': [{
                'outpoint': 'test_outpoint',
                'amount': order.btc_amount,
            }],
            'create_raw_transaction.return_value': 'test_tx',
            'sign_raw_transaction.return_value': 'test_tx_signed',
            'send_raw_transaction.return_value': refund_tx_id,
        })

        payment.reverse_payment(order)
        tx_outputs = bc_mock.create_raw_transaction.call_args[0][1]
        self.assertEqual(tx_outputs[order.refund_address],
                         Decimal('0.101'))
        self.assertTrue(bc_mock.sign_raw_transaction.called)
        self.assertTrue(bc_mock.send_raw_transaction.called)
        order.refresh_from_db()
        self.assertEqual(order.refund_tx_id, refund_tx_id)
        self.assertEqual(order.status, 'refunded')

    def test_already_forwarded(self):
        order = PaymentOrderFactory.create(
            time_recieved=timezone.now(),
            time_forwarded=timezone.now())
        with self.assertRaises(exceptions.RefundError):
            payment.reverse_payment(order)

    def test_already_refunded(self):
        order = PaymentOrderFactory.create(
            time_recieved=timezone.now(),
            time_refunded=timezone.now())
        with self.assertRaises(exceptions.RefundError):
            payment.reverse_payment(order)

    @patch('operations.payment.blockchain.BlockChain')
    def test_nothing_to_send(self, bc_cls_mock):
        order = PaymentOrderFactory.create(
            merchant_btc_amount=Decimal('0.1'),
            fee_btc_amount=Decimal('0.001'),
            btc_amount=Decimal('0.1011'),
            refund_address='1KYwqZshnYNUNweXrDkCAdLaixxPhePRje')
        bc_cls_mock.return_value = Mock(**{
            'get_unspent_outputs.return_value': [],
        })
        with self.assertRaises(exceptions.RefundError):
            payment.reverse_payment(order)


class WaitForValidationTestCase(TestCase):

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.forward_transaction')
    def test_payment_order_does_not_exist(self, forward_mock, cancel_mock):
        payment.wait_for_validation(123456)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(forward_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.forward_transaction')
    def test_payment_not_validated(self, forward_mock, cancel_mock):
        payment_order = PaymentOrderFactory.create()
        self.assertIsNone(payment_order.time_recieved)
        payment.wait_for_validation(payment_order.uid)
        self.assertFalse(cancel_mock.called)
        self.assertFalse(forward_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.forward_transaction')
    def test_payment_already_forwarded(self, forward_mock, cancel_mock):
        payment_order = PaymentOrderFactory.create(
            time_recieved=timezone.now(),
            time_forwarded=timezone.now(),
            incoming_tx_ids=['0' * 64],
            outgoing_tx_id='0' * 64)
        payment.wait_for_validation(payment_order.uid)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(forward_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.forward_transaction')
    def test_payment_cancelled_1(self, forward_mock, cancel_mock):
        order = PaymentOrderFactory.create(
            time_cancelled=timezone.now())
        payment.wait_for_validation(order.uid)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(forward_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockcypher.is_tx_reliable')
    @patch('operations.payment.forward_transaction')
    @patch('operations.payment.run_periodic_task')
    def test_payment_cancelled_2(self, run_task_mock, forward_mock,
                                 conf_chk_mock, cancel_mock):
        order = PaymentOrderFactory.create(
            time_recieved=timezone.now(),
            incoming_tx_ids=['0' * 64])

        def cancel_order():
            order.time_cancelled = timezone.now()
            order.save()

        conf_chk_mock.return_value = True
        # Cancel order while checking for confidence
        conf_chk_mock.side_effect = cancel_order

        payment.wait_for_validation(order.uid)
        self.assertTrue(conf_chk_mock.called)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(forward_mock.called)
        self.assertFalse(run_task_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockcypher.is_tx_reliable')
    @patch('operations.payment.forward_transaction')
    def test_tx_not_reliable(self, forward_mock, conf_chk_mock, cancel_mock):
        conf_chk_mock.return_value = False
        payment_order = PaymentOrderFactory.create(
            time_recieved=timezone.now(),
            incoming_tx_ids=['0' * 64])
        payment.wait_for_validation(payment_order.uid)
        self.assertFalse(cancel_mock.called)
        self.assertFalse(forward_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockcypher.is_tx_reliable')
    @patch('operations.payment.forward_transaction')
    def test_multiple_tx_not_reliable(self, forward_mock,
                                      conf_chk_mock, cancel_mock):
        conf_chk_mock.side_effect = [False, False]
        payment_order = PaymentOrderFactory.create(
            time_recieved=timezone.now(),
            incoming_tx_ids=['0' * 64, '1' * 64])
        payment.wait_for_validation(payment_order.uid)
        self.assertEqual(conf_chk_mock.call_count, 1)
        self.assertFalse(cancel_mock.called)
        self.assertFalse(forward_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockcypher.is_tx_reliable')
    @patch('operations.payment.forward_transaction')
    def test_blockcypher_error(self, forward_mock, conf_chk_mock, cancel_mock):
        conf_chk_mock.side_effect = ValueError
        payment_order = PaymentOrderFactory.create(
            time_recieved=timezone.now(),
            incoming_tx_ids=['0' * 64])
        payment.wait_for_validation(payment_order.uid)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(forward_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockcypher.is_tx_reliable')
    @patch('operations.payment.forward_transaction')
    @patch('operations.payment.run_periodic_task')
    def test_forward_btc(self, run_task_mock, forward_mock, conf_chk_mock,
                         cancel_mock):
        conf_chk_mock.return_value = True
        payment_order = PaymentOrderFactory.create(
            time_recieved=timezone.now(),
            incoming_tx_ids=['0' * 64])
        payment.wait_for_validation(payment_order.uid)

        self.assertTrue(cancel_mock.called)
        self.assertTrue(forward_mock.called)
        self.assertEqual(forward_mock.call_args[0][0].uid,
                         payment_order.uid)
        self.assertEqual(run_task_mock.call_count, 1)
        self.assertEqual(run_task_mock.call_args[0][0].__name__,
                         'wait_for_confirmation')

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockcypher.is_tx_reliable')
    @patch('operations.payment.forward_transaction')
    @patch('operations.payment.run_periodic_task')
    def test_forward_btc_multiple_tx(self, run_task_mock, forward_mock,
                                     conf_chk_mock, cancel_mock):
        conf_chk_mock.side_effect = [True, True]
        payment_order = PaymentOrderFactory.create(
            time_recieved=timezone.now(),
            incoming_tx_ids=['0' * 64, '1' * 64])
        payment.wait_for_validation(payment_order.uid)
        self.assertTrue(cancel_mock.called)
        self.assertTrue(forward_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockcypher.is_tx_reliable')
    @patch('operations.payment.forward_transaction')
    @patch('operations.payment.run_periodic_task')
    def test_forward_instantfiat(self, run_task_mock, forward_mock,
                                 conf_chk_mock, cancel_mock):
        conf_chk_mock.return_value = True
        payment_order = PaymentOrderFactory.create(
            time_recieved=timezone.now(),
            incoming_tx_ids=['0' * 64],
            instantfiat_invoice_id='test_invoice')
        payment.wait_for_validation(payment_order.uid)

        self.assertTrue(cancel_mock.called)
        self.assertTrue(forward_mock.called)
        self.assertEqual(run_task_mock.call_count, 2)
        calls = run_task_mock.call_args_list
        self.assertEqual(calls[0][0][0].__name__, 'wait_for_confirmation')
        self.assertEqual(calls[1][0][0].__name__, 'wait_for_exchange')


class ForwardTransactionTestCase(TestCase):

    @patch('operations.payment.blockchain.BlockChain')
    def test_forward_standard(self, bc_mock):
        payment_order = PaymentOrderFactory.create(
            merchant_btc_amount=Decimal('0.1'),
            fee_btc_amount=Decimal('0.001'),
            btc_amount=Decimal('0.1011'),
            instantfiat_btc_amount=Decimal(0),
            incoming_tx_ids=['0' * 64],
            refund_address='18GV9EWUjSVTU1jXMb1RmaGxAonSyBgKAc')
        AccountFactory.create(merchant=payment_order.device.merchant)
        outgoing_tx_id = '1' * 64
        extra_btc_amount = Decimal('0.001')

        bc_instance_mock = Mock(**{
            'get_raw_transaction.return_value': 'test_incoming_tx',
            'get_unspent_outputs.return_value': [{
                'outpoint': 'test_outpoint',
                'amount': payment_order.btc_amount + extra_btc_amount,
            }],
            'create_raw_transaction.return_value': 'test_tx',
            'sign_raw_transaction.return_value': 'test_tx_signed',
            'send_raw_transaction.return_value': outgoing_tx_id,
        })
        bc_mock.return_value = bc_instance_mock

        payment.forward_transaction(payment_order)

        self.assertTrue(bc_instance_mock.get_raw_transaction.called)
        self.assertTrue(bc_instance_mock.get_unspent_outputs.called)
        args = bc_instance_mock.get_unspent_outputs.call_args[0]
        self.assertEqual(str(args[0]), payment_order.local_address)

        self.assertTrue(bc_instance_mock.create_raw_transaction.called)
        args = bc_instance_mock.create_raw_transaction.call_args[0]
        self.assertEqual(args[0], ['test_outpoint'])
        outputs = args[1]
        self.assertEqual(len(outputs.keys()), 3)
        self.assertEqual(outputs[payment_order.merchant_address],
                         payment_order.merchant_btc_amount)
        self.assertEqual(outputs[payment_order.fee_address],
                         payment_order.fee_btc_amount)
        self.assertEqual(outputs[payment_order.refund_address],
                         payment_order.extra_btc_amount)

        self.assertTrue(bc_instance_mock.sign_raw_transaction.called)
        self.assertTrue(bc_instance_mock.send_raw_transaction.called)

        payment_order.refresh_from_db()
        self.assertEqual(payment_order.extra_btc_amount, extra_btc_amount)
        self.assertEqual(payment_order.tx_fee_btc_amount, Decimal('0.0001'))
        self.assertEqual(payment_order.outgoing_tx_id, outgoing_tx_id)
        self.assertIsNotNone(payment_order.time_forwarded)

    @patch('operations.payment.blockchain.BlockChain')
    def test_forward_dust_extra(self, bc_cls_mock):
        order = PaymentOrderFactory.create(
            merchant_btc_amount=Decimal('0.1'),
            fee_btc_amount=Decimal('0.001'),
            btc_amount=Decimal('0.1011'),
            instantfiat_btc_amount=Decimal(0),
            incoming_tx_ids=['0' * 64])
        AccountFactory.create(merchant=order.device.merchant)
        bc_cls_mock.return_value = Mock(**{
            'get_raw_transaction.return_value': 'test_incoming_tx',
            'get_unspent_outputs.return_value': [{
                'outpoint': 'test_outpoint',
                'amount': order.btc_amount + Decimal('0.00005'),
            }],
            'create_raw_transaction.return_value': 'test_tx',
            'sign_raw_transaction.return_value': 'test_tx_signed',
            'send_raw_transaction.return_value': '1' * 64,
        })

        payment.forward_transaction(order)
        order.refresh_from_db()
        self.assertEqual(order.extra_btc_amount, 0)
        self.assertEqual(order.tx_fee_btc_amount, Decimal('0.00015'))
        self.assertIsNotNone(order.time_forwarded)

    @patch('operations.payment.blockchain.BlockChain')
    def test_forward_balance(self, bc_mock):
        merchant = MerchantAccountFactory.create()
        btc_account = AccountFactory.create(merchant=merchant,
                                            balance_max=Decimal('1.0'))
        payment_order = PaymentOrderFactory.create(
            device__merchant=merchant,
            merchant_btc_amount=Decimal('0.1'),
            fee_btc_amount=Decimal('0.001'),
            btc_amount=Decimal('0.1011'),
            instantfiat_btc_amount=Decimal(0),
            incoming_tx_ids=['0' * 64])
        outgoing_tx_id = '1' * 64
        account_address = '13tmm98hpFexSa3gi15DdD1p4kN2WsEBXX'

        bc_instance_mock = Mock(**{
            'get_raw_transaction.return_value': 'test_incoming_tx',
            'get_unspent_outputs.return_value': [{
                'outpoint': 'test_outpoint',
                'amount': payment_order.btc_amount,
            }],
            'get_new_address.return_value': account_address,
            'create_raw_transaction.return_value': 'test_tx',
            'sign_raw_transaction.return_value': 'test_tx_signed',
            'send_raw_transaction.return_value': outgoing_tx_id,
        })
        bc_mock.return_value = bc_instance_mock

        payment.forward_transaction(payment_order)

        self.assertTrue(bc_instance_mock.get_new_address.called)

        outputs = bc_instance_mock.create_raw_transaction.call_args[0][1]
        self.assertEqual(len(outputs.keys()), 2)
        self.assertEqual(outputs[account_address],
                         payment_order.merchant_btc_amount)
        self.assertEqual(outputs[payment_order.fee_address],
                         payment_order.fee_btc_amount)

        payment_order = PaymentOrder.objects.get(pk=payment_order.pk)
        self.assertEqual(payment_order.extra_btc_amount, 0)
        self.assertEqual(payment_order.outgoing_tx_id, outgoing_tx_id)
        self.assertIsNotNone(payment_order.time_forwarded)

        btc_account = Account.objects.get(pk=btc_account.pk)
        self.assertEqual(btc_account.bitcoin_address, account_address)
        self.assertEqual(btc_account.balance,
                         payment_order.merchant_btc_amount)


class WaitForConfirmationTestCase(TestCase):

    @patch('operations.payment.cancel_current_task')
    def test_payment_order_does_not_exist(self, cancel_mock):
        payment.wait_for_confirmation(123456)
        self.assertTrue(cancel_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockchain.BlockChain')
    def test_tx_confirmed(self, bc_cls_mock, cancel_mock):
        order = PaymentOrderFactory.create(
            outgoing_tx_id='0' * 64)
        bc_cls_mock.return_value = Mock(**{
            'is_tx_confirmed.return_value': True,
        })
        payment.wait_for_confirmation(order.uid)
        order.refresh_from_db()
        self.assertIsNotNone(order.time_confirmed)
        self.assertTrue(cancel_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.blockchain.BlockChain')
    def test_tx_not_broadcasted(self, bc_cls_mock, cancel_mock):
        order = PaymentOrderFactory.create(
            outgoing_tx_id='0' * 64)
        bc_cls_mock.return_value = Mock(**{
            'is_tx_confirmed.return_value': False,
        })
        payment.wait_for_confirmation(order.uid)
        order.refresh_from_db()
        self.assertIsNone(order.time_confirmed)
        self.assertFalse(cancel_mock.called)


class CheckPaymentStatusTestCase(TestCase):

    @patch('operations.payment.cancel_current_task')
    def test_order_does_not_exist(self, cancel_mock):
        payment.check_payment_status(123456)
        self.assertTrue(cancel_mock.called)

    @patch('operations.payment.cancel_current_task')
    def test_new(self, cancel_mock):
        order = PaymentOrderFactory.create()
        payment.check_payment_status(order.uid)
        self.assertFalse(cancel_mock.called)

    @patch('operations.payment.cancel_current_task')
    def test_notified(self, cancel_mock):
        order = PaymentOrderFactory.create(time_notified=timezone.now())
        payment.check_payment_status(order.uid)
        self.assertFalse(cancel_mock.called)

    @patch('operations.payment.cancel_current_task')
    def test_confirmed(self, cancel_mock):
        order = PaymentOrderFactory.create(
            time_notified=timezone.now(),
            time_confirmed=timezone.now())
        payment.check_payment_status(order.uid)
        self.assertTrue(cancel_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.send_error_message')
    @patch('operations.payment.reverse_payment')
    def test_failed(self, reverse_mock, send_mock, cancel_mock):
        order = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=2),
            time_recieved=timezone.now() - datetime.timedelta(hours=1))
        payment.check_payment_status(order.uid)
        self.assertTrue(cancel_mock.called)
        self.assertTrue(send_mock.called)
        self.assertEqual(send_mock.call_args[1]['order'].pk, order.pk)
        self.assertTrue(reverse_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.send_error_message')
    def test_unconfirmed(self, send_mock, cancel_mock):
        order = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=4),
            time_recieved=timezone.now() - datetime.timedelta(hours=3),
            time_forwarded=timezone.now() - datetime.timedelta(hours=3),
            time_notified=timezone.now() - datetime.timedelta(hours=3))
        self.assertEqual(order.status, 'unconfirmed')
        payment.check_payment_status(order.uid)
        self.assertTrue(cancel_mock.called)
        self.assertTrue(send_mock.called)
        self.assertEqual(send_mock.call_args[1]['order'].pk, order.pk)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.send_error_message')
    def test_refunded(self, send_mock, cancel_mock):
        order = PaymentOrderFactory.create(
            time_created=timezone.now(),
            time_recieved=timezone.now(),
            time_refunded=timezone.now())
        payment.check_payment_status(order.uid)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(send_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.send_error_message')
    @patch('operations.payment.reverse_payment')
    def test_cancelled(self, reverse_mock, send_mock, cancel_mock):
        order = PaymentOrderFactory.create(
            time_cancelled=timezone.now())
        payment.check_payment_status(order.uid)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(send_mock.called)
        self.assertTrue(reverse_mock.called)

    @patch('operations.payment.cancel_current_task')
    @patch('operations.payment.send_error_message')
    @patch('operations.payment.reverse_payment')
    def test_timeout(self, reverse_mock, send_mock, cancel_mock):
        order = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=1))
        payment.check_payment_status(order.uid)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(send_mock.called)
        self.assertTrue(reverse_mock.called)

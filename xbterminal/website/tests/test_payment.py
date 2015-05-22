from decimal import Decimal
from django.test import TestCase
from mock import patch, Mock

from constance import config
from website.models import PaymentOrder
from website.tests.factories import DeviceFactory, PaymentOrderFactory
from payment import tasks
from payment import BTC_DEC_PLACES


class PreparePaymentTestCase(TestCase):

    fixtures = ['initial_data.json']

    @patch('payment.tasks.blockchain.BlockChain')
    @patch('payment.tasks.average.get_exchange_rate')
    @patch('payment.tasks.run_periodic_task')
    def test_keep_btc(self, run_task_mock, get_rate_mock, bc_mock):
        device = DeviceFactory.create(
            percent=0,
            bitcoin_address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        fiat_amount = Decimal('10')
        exchange_rate = Decimal('235.64')
        local_address = '1KYwqZshnYNUNweXrDkCAdLaixxPhePRje'

        bc_mock.return_value = Mock(**{
            'get_new_address.return_value': local_address,
        })
        get_rate_mock.return_value = exchange_rate

        payment_order = tasks.prepare_payment(device, fiat_amount)
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
        self.assertEqual(payment_order.fiat_currency,
                         device.merchant.currency.name)
        self.assertEqual(payment_order.fiat_amount, fiat_amount)
        self.assertEqual(payment_order.instantfiat_fiat_amount, 0)
        self.assertEqual(payment_order.instantfiat_btc_amount, 0)
        self.assertEqual(payment_order.merchant_btc_amount,
                         expected_merchant_btc_amount)
        self.assertEqual(payment_order.fee_btc_amount,
                         expected_fee_btc_amount)
        self.assertEqual(payment_order.btc_amount,
                         expected_btc_amount)
        self.assertIsNone(payment_order.instantfiat_invoice_id)
        self.assertIsNone(payment_order.incoming_tx_id)
        self.assertIsNone(payment_order.outgoing_tx_id)
        self.assertIsNone(payment_order.transaction)
        self.assertIsNone(payment_order.receipt_key)
        self.assertEqual(payment_order.status, 'new')

        calls = run_task_mock.call_args_list
        self.assertEqual(calls[0][0][0].__name__, 'wait_for_payment')
        self.assertEqual(calls[1][0][0].__name__, 'wait_for_validation')
        self.assertEqual(calls[2][0][0].__name__, 'check_payment_status')

    @patch('payment.tasks.blockchain.BlockChain')
    @patch('payment.tasks.average.get_exchange_rate')
    @patch('payment.tasks.run_periodic_task')
    def test_keep_btc_without_fee(self, run_task_mock, get_rate_mock, bc_mock):
        device = DeviceFactory.create(
            device_type='hardware',
            percent=0,
            bitcoin_address='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        fiat_amount = Decimal('1')
        exchange_rate = Decimal('235.64')
        local_address = '1KYwqZshnYNUNweXrDkCAdLaixxPhePRje'

        bc_mock.return_value = Mock(**{
            'get_new_address.return_value': local_address,
        })
        get_rate_mock.return_value = exchange_rate

        payment_order = tasks.prepare_payment(device, fiat_amount)
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

    @patch('payment.tasks.blockchain.BlockChain')
    @patch('payment.tasks.instantfiat.create_invoice')
    @patch('payment.tasks.run_periodic_task')
    def test_convert_full(self, run_task_mock, invoice_mock, bc_mock):
        device = DeviceFactory.create(percent=100, bitcoin_address='')
        fiat_amount = Decimal('10')
        local_address = '1KYwqZshnYNUNweXrDkCAdLaixxPhePRje'
        instantfiat_invoice_id = 'test_invoice_123'
        instantfiat_btc_amount = Decimal('0.043')
        instantfiat_address = '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'

        bc_mock.return_value = Mock(**{
            'get_new_address.return_value': local_address,
        })
        invoice_mock.return_value = {
            'instantfiat_invoice_id': instantfiat_invoice_id,
            'instantfiat_btc_amount': instantfiat_btc_amount,
            'instantfiat_address': instantfiat_address,
        }

        payment_order = tasks.prepare_payment(device, fiat_amount)
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


class WaitForPaymentTestCase(TestCase):

    fixtures = ['initial_data.json']

    @patch('payment.tasks.cancel_current_task')
    @patch('payment.tasks.blockchain.BlockChain')
    def test_payment_order_does_not_exist(self, bc_mock, cancel_mock):
        tasks.wait_for_payment(123456)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(bc_mock.called)

    @patch('payment.tasks.cancel_current_task')
    @patch('payment.tasks.blockchain.BlockChain')
    def test_payment_already_validated(self, bc_mock, cancel_mock):
        payment_order = PaymentOrderFactory.create(
            incoming_tx_id='0' * 64)
        tasks.wait_for_payment(payment_order.uid)
        self.assertTrue(cancel_mock.called)
        self.assertFalse(bc_mock.called)

    @patch('payment.tasks.cancel_current_task')
    @patch('payment.tasks.blockchain.BlockChain')
    @patch('payment.tasks.validate_payment')
    def test_no_transactions(self, validate_mock, bc_mock, cancel_mock):
        bc_instance_mock = Mock(**{
            'get_unspent_transactions.return_value': [],
        })
        bc_mock.return_value = bc_instance_mock

        payment_order = PaymentOrderFactory.create()
        tasks.wait_for_payment(payment_order.uid)
        self.assertFalse(cancel_mock.called)
        self.assertTrue(bc_instance_mock.get_unspent_transactions.called)
        self.assertFalse(validate_mock.called)

    @patch('payment.tasks.cancel_current_task')
    @patch('payment.tasks.blockchain.BlockChain')
    @patch('payment.tasks.validate_payment')
    def test_validate_payment(self, validate_mock, bc_mock, cancel_mock):
        bc_instance_mock = Mock(**{
            'get_unspent_transactions.return_value': ['test_tx'],
        })
        bc_mock.return_value = bc_instance_mock

        payment_order = PaymentOrderFactory.create()
        tasks.wait_for_payment(payment_order.uid)

        self.assertTrue(bc_instance_mock.get_unspent_transactions.called)
        args = bc_instance_mock.get_unspent_transactions.call_args[0]
        self.assertEqual(str(args[0]), payment_order.local_address)

        self.assertTrue(validate_mock.called)
        args = validate_mock.call_args[0]
        self.assertEqual(args[0].uid, payment_order.uid)
        self.assertEqual(args[1], ['test_tx'])
        self.assertEqual(args[2], 'bip0021')

        self.assertTrue(cancel_mock.called)


class ValidatePaymentTestCase(TestCase):

    fixtures = ['initial_data.json']

    @patch('payment.tasks.blockchain.BlockChain')
    @patch('payment.tasks.blockchain.get_txid')
    def test_bip0021(self, get_txid_mock, bc_mock):
        payment_order = PaymentOrderFactory.create()
        incoming_tx = Mock()
        incoming_tx_id = '0' * 64
        refund_address = '1KYwqZshnYNUNweXrDkCAdLaixxPhePRje'

        bc_instance_mock = Mock(**{
            'sign_raw_transaction.return_value': Mock(),
            'get_tx_inputs.return_value': [{'address': refund_address}],
            'get_tx_outputs.return_value': [{
                'address': payment_order.local_address,
                'amount': payment_order.btc_amount,
            }],
        })
        bc_mock.return_value = bc_instance_mock
        get_txid_mock.return_value = incoming_tx_id

        tasks.validate_payment(payment_order, [incoming_tx], 'bip0021')

        self.assertTrue(bc_instance_mock.sign_raw_transaction.called)
        self.assertFalse(bc_instance_mock.send_raw_transaction.called)

        payment_order = PaymentOrder.objects.get(uid=payment_order.uid)
        self.assertEqual(payment_order.refund_address, refund_address)
        self.assertEqual(payment_order.incoming_tx_id, incoming_tx_id)
        self.assertEqual(payment_order.payment_type, 'bip0021')
        self.assertEqual(payment_order.status, 'recieved')

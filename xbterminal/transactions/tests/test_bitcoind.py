from decimal import Decimal
from django.test import TestCase, override_settings
from mock import patch, Mock

import bitcoin
from bitcoin.core import COutPoint, lx
from constance.test import override_config

from transactions.exceptions import TransactionModified, DoubleSpend
from transactions.constants import BTC_MIN_FEE
from transactions.services.bitcoind import (
    BlockChain,
    serialize_outputs,
    deserialize_outputs,
    validate_bitcoin_address,
    split_amount,
    get_tx_fee)


class BlockChainTestCase(TestCase):

    @patch('transactions.services.bitcoind.bitcoin.SelectParams')
    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_init(self, proxy_cls_mock, select_params_mock):
        BlockChain('mainnet')
        self.assertTrue(select_params_mock.called)
        self.assertEqual(select_params_mock.call_args[0][0], 'mainnet')
        self.assertTrue(proxy_cls_mock.called)
        service_url = proxy_cls_mock.call_args[0][0]
        self.assertTrue(service_url.startswith('http'))

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_import_address(self, proxy_cls_mock):
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'importaddress.return_value': None,
        })
        address = '1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6'
        bc = BlockChain('mainnet')
        bc.import_address('1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6')
        self.assertEqual(proxy_mock.importaddress.call_count, 1)
        self.assertEqual(proxy_mock.importaddress.call_args[0][0], address)
        self.assertIs(proxy_mock.importaddress.call_args[1]['rescan'], False)

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_get_balance(self, proxy_cls_mock):
        proxy_cls_mock.return_value = Mock(**{
            'getbalance.return_value': 500000,
        })
        bc = BlockChain('mainnet')
        balance = bc.get_balance()
        self.assertEqual(balance, Decimal('0.005'))

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_get_address_balance(self, proxy_cls_mock):
        proxy_cls_mock.return_value = Mock(**{
            'listunspent.return_value': [{'amount': 500000}],
        })
        bc = BlockChain('mainnet')
        balance = bc.get_address_balance('test')
        self.assertEqual(balance, Decimal('0.005'))

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_get_unspent_outputs(self, proxy_cls_mock):
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'listunspent.return_value': [{
                'amount': 500000, 'outpoint': Mock(),
            }],
        })
        bc = BlockChain('mainnet')
        outputs = bc.get_unspent_outputs('test', minconf=1)
        self.assertEqual(outputs[0]['amount'], Decimal('0.005'))
        self.assertTrue(proxy_mock.listunspent.called)
        self.assertEqual(proxy_mock.listunspent.call_args[1]['minconf'], 1)

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_get_raw_unspent_outputs(self, proxy_cls_mock):
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'call.return_value': [{'txid': '1' * 64}],
        })
        bc = BlockChain('mainnet')
        outputs = bc.get_raw_unspent_outputs('test', minconf=1)
        self.assertEqual(outputs[0]['txid'], '1' * 64)
        self.assertTrue(proxy_mock.call.call_args[0][0], 'listunspent')
        self.assertEqual(proxy_mock.call.call_args[0][1], 1)
        self.assertEqual(proxy_mock.call.call_args[0][2], 9999999)
        self.assertEqual(proxy_mock.call.call_args[0][3], ['test'])

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_get_unspent_transactions(self, proxy_cls_mock):
        address = '1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6'
        transaction_mock = Mock()
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'listunspent.return_value': [{
                'amount': 500000, 'outpoint': Mock(hash=b'\x11' * 32),
            }],
            'getrawtransaction.return_value': transaction_mock,
        })
        bc = BlockChain('mainnet')
        transactions = bc.get_unspent_transactions(address)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0], transaction_mock)
        self.assertEqual(proxy_mock.listunspent.call_count, 1)
        self.assertEqual(proxy_mock.listunspent.call_args[1]['minconf'], 0)
        call_addrs = proxy_mock.listunspent.call_args[1]['addrs']
        self.assertEqual(len(call_addrs), 1)
        self.assertEqual(call_addrs[0].__class__.__name__,
                         'P2PKHBitcoinAddress')
        self.assertEqual(
            proxy_mock.getrawtransaction.call_args[0][0],
            b'\x11' * 32)

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_is_tx_valid(self, proxy_cls_mock):
        proxy_cls_mock.return_value = Mock(**{
            'signrawtransaction.return_value': {
                'tx': 'tx',
                'complete': True,
            },
        })
        bc = BlockChain('mainnet')
        result = bc.is_tx_valid(Mock())
        self.assertIs(result, True)

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    @patch('transactions.services.bitcoind.get_txid')
    def test_is_tx_valid_confirmed(self, get_txid_mock, proxy_cls_mock):
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'signrawtransaction.return_value': {
                'tx': 'tx',
                'complete': False,
            },
            'gettransaction.return_value': {
                'confirmations': 1,
                'walletconflicts': [],
            },
        })
        get_txid_mock.return_value = tx_id = '1' * 64
        bc = BlockChain('mainnet')
        result = bc.is_tx_valid(Mock())
        self.assertIs(result, True)
        self.assertIs(proxy_mock.gettransaction.called, True)
        self.assertEqual(proxy_mock.gettransaction.call_args[0][0],
                         lx(tx_id))

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    @patch('transactions.services.bitcoind.get_txid')
    def test_is_tx_valid_invalid(self, get_txid_mock, proxy_cls_mock):
        proxy_cls_mock.return_value = Mock(**{
            'signrawtransaction.return_value': {
                'tx': 'tx',
                'complete': False,
            },
            'gettransaction.return_value': {
                'confirmations': 0,
                'walletconflicts': [],
            },
        })
        get_txid_mock.return_value = '1' * 64
        bc = BlockChain('mainnet')
        result = bc.is_tx_valid(Mock())
        self.assertIs(result, False)

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_is_tx_confirmed_true(self, proxy_cls_mock):
        tx_id = '1' * 64
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'gettransaction.return_value': {
                'confirmations': 6,
                'walletconflicts': [],
            },
        })
        bc = BlockChain('mainnet')
        self.assertIs(bc.is_tx_confirmed(tx_id), True)
        self.assertEqual(proxy_mock.gettransaction.call_args[0][0],
                         lx(tx_id))

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_is_tx_confirmed_false(self, proxy_cls_mock):
        tx_id = '1' * 64
        proxy_cls_mock.return_value = Mock(**{
            'gettransaction.return_value': {
                'confirmations': 1,
                'walletconflicts': [],
            },
        })
        bc = BlockChain('mainnet')
        self.assertIs(bc.is_tx_confirmed(tx_id), False)

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_is_tx_confirmed_modified(self, proxy_cls_mock):
        tx_id_1 = '1' * 64
        tx_id_2 = '2' * 64
        proxy_cls_mock.return_value = Mock(**{
            'gettransaction.return_value': {
                'confirmations': 0,
                'walletconflicts': [tx_id_2],
            },
            'getrawtransaction.side_effect': [
                {'confirmations': 6, 'tx': Mock(vout='test')},
                Mock(vout='test'),
            ],
        })
        bc = BlockChain('mainnet')
        with self.assertRaises(TransactionModified) as context:
            bc.is_tx_confirmed(tx_id_1)
        self.assertEqual(context.exception.another_tx_id, tx_id_2)

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_is_tx_confirmed_double_spend(self, proxy_cls_mock):
        tx_id_1 = '1' * 64
        tx_id_2 = '2' * 64
        proxy_cls_mock.return_value = Mock(**{
            'gettransaction.return_value': {
                'confirmations': 0,
                'walletconflicts': [tx_id_2],
            },
            'getrawtransaction.side_effect': [
                {'confirmations': 6, 'tx': Mock(vout='one')},
                Mock(vout='two'),
            ],
        })
        bc = BlockChain('mainnet')
        with self.assertRaises(DoubleSpend) as context:
            bc.is_tx_confirmed(tx_id_1)
        self.assertEqual(context.exception.another_tx_id, tx_id_2)

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_get_tx_fee(self, proxy_cls_mock):
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'call.return_value': Decimal('0.0002'),
        })
        bc = BlockChain('mainnet')
        expected_fee = get_tx_fee(1, 1, Decimal('0.0002'))
        self.assertEqual(bc.get_tx_fee(1, 1), expected_fee)
        self.assertEqual(proxy_mock.call.call_count, 1)
        self.assertEqual(proxy_mock.call.call_args[0][0], 'estimatefee')
        self.assertEqual(proxy_mock.call.call_args[0][1], 10)

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    @override_config(TX_DEFAULT_FEE=Decimal('0.0005'))
    def test_get_tx_fee_error(self, proxy_cls_mock):
        proxy_cls_mock.return_value = Mock(**{
            'call.return_value': Decimal(-1),
        })
        bc = BlockChain('mainnet')
        expected_fee = get_tx_fee(1, 1, Decimal('0.0005'))
        self.assertEqual(bc.get_tx_fee(1, 1), expected_fee)

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    @override_config(TX_DEFAULT_FEE=Decimal('0.0015'))
    @override_settings(DEBUG=True)
    def test_get_tx_fee_debug(self, proxy_cls_mock):
        proxy_cls_mock.return_value = Mock(**{
            'call.return_value': Decimal('0.0009'),
        })
        bc = BlockChain('mainnet')
        expected_fee = get_tx_fee(1, 1, Decimal('0.0015'))
        self.assertEqual(bc.get_tx_fee(1, 1), expected_fee)

    @patch('transactions.services.bitcoind.bitcoin.rpc.Proxy')
    def test_get_tx_fee_too_small(self, proxy_cls_mock):
        proxy_cls_mock.return_value = Mock(**{
            'call.return_value': Decimal('0.00000223'),
        })
        bc = BlockChain('mainnet')
        expected_fee = get_tx_fee(1, 1, BTC_MIN_FEE)
        self.assertEqual(bc.get_tx_fee(1, 1), expected_fee)


class UtilsTestCase(TestCase):

    def test_output_serialization(self):
        outputs = [COutPoint(n=1), COutPoint(n=2)]
        serialized = serialize_outputs(outputs)
        deserialized = deserialize_outputs(serialized)
        self.assertEqual(len(deserialized), 2)

    def test_address_validation(self):
        self.assertEqual(bitcoin.params.__class__.__name__, 'MainParams')
        main_addr = '1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6'
        self.assertIsNone(
            validate_bitcoin_address(main_addr, 'mainnet'))
        test_addr = 'mxqpfcxzKnPfgZw8JKs7DU6m7DTysxBBWn'
        self.assertIsNone(
            validate_bitcoin_address(test_addr, 'testnet'))
        self.assertIsNotNone(
            validate_bitcoin_address(test_addr, 'mainnet'))
        invalid_addr = '1wFSdAv9rGpA4CvX3UtxZpUwaumsWM68pC'
        self.assertIsNotNone(
            validate_bitcoin_address(invalid_addr, None))
        self.assertEqual(bitcoin.params.__class__.__name__, 'MainParams')

    def test_split_amount(self):
        max_size = Decimal('0.05')
        splitted_1 = split_amount(Decimal('0.01'), max_size)
        self.assertEqual(splitted_1, [Decimal('0.01')])
        splitted_2 = split_amount(Decimal('0.05'), max_size)
        self.assertEqual(splitted_2, [Decimal('0.05')])
        splitted_3 = split_amount(Decimal('0.13'), max_size)
        self.assertEqual(
            splitted_3,
            [Decimal('0.05'), Decimal('0.05'), Decimal('0.03')])

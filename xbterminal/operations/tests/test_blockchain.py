from decimal import Decimal
from django.test import TestCase
from mock import patch, Mock

import bitcoin
from bitcoin.core import COutPoint
from operations.blockchain import (
    BlockChain,
    serialize_outputs,
    deserialize_outputs,
    validate_bitcoin_address,
    split_amount)


class BlockChainTestCase(TestCase):

    @patch('operations.blockchain.bitcoin.SelectParams')
    @patch('operations.blockchain.bitcoin.rpc.Proxy')
    def test_init(self, proxy_mock, select_params_mock):
        BlockChain('mainnet')
        self.assertTrue(select_params_mock.called)
        self.assertEqual(select_params_mock.call_args[0][0], 'mainnet')
        self.assertTrue(proxy_mock.called)
        service_url = proxy_mock.call_args[0][0]
        self.assertTrue(service_url.startswith('http'))

    @patch('operations.blockchain.bitcoin.rpc.Proxy')
    def test_get_balance(self, proxy_mock):
        proxy_mock.return_value = Mock(**{
            'getbalance.return_value': 500000,
        })
        bc = BlockChain('mainnet')
        balance = bc.get_balance()
        self.assertEqual(balance, Decimal('0.005'))

    @patch('operations.blockchain.bitcoin.rpc.Proxy')
    def test_get_address_balance(self, proxy_mock):
        proxy_mock.return_value = Mock(**{
            'listunspent.return_value': [{'amount': 500000}],
        })
        bc = BlockChain('mainnet')
        balance = bc.get_address_balance('test')
        self.assertEqual(balance, Decimal('0.005'))

    @patch('operations.blockchain.bitcoin.rpc.Proxy')
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

    @patch('operations.blockchain.bitcoin.rpc.Proxy')
    def test_is_tx_confirmed(self, proxy_mock):
        # Confirmed
        proxy_mock.return_value = Mock(**{
            'gettransaction.return_value': {'confirmations': 2},
        })
        bc = BlockChain('mainnet')
        self.assertTrue(bc.is_tx_confirmed('0' * 64))
        # Unconfirmed
        proxy_mock.return_value = Mock(**{
            'gettransaction.return_value': {'confirmations': 0},
        })
        bc = BlockChain('mainnet')
        self.assertFalse(bc.is_tx_confirmed('0' * 64))


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

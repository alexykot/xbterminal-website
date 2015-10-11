from decimal import Decimal
from django.test import TestCase
from mock import patch, Mock

import bitcoin
from bitcoin.core import COutPoint
from operations.blockchain import (
    BlockChain,
    serialize_outputs,
    deserialize_outputs,
    validate_bitcoin_address)


class BlockChainTestCase(TestCase):

    @patch('operations.blockchain.bitcoin.SelectParams')
    @patch('operations.blockchain.bitcoin.rpc.Proxy')
    def test_init(self, proxy_mock, select_params_mock):
        bc = BlockChain('mainnet')
        self.assertTrue(select_params_mock.called)
        self.assertEqual(select_params_mock.call_args[0][0], 'mainnet')
        self.assertTrue(proxy_mock.called)
        service_url = proxy_mock.call_args[0][0]
        self.assertTrue(service_url.startswith('https'))

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

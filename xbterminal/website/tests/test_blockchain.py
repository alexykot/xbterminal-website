from decimal import Decimal
from django.test import TestCase
from mock import patch, Mock

from payment.blockchain import BlockChain


class BlockChainTestCase(TestCase):

    @patch('payment.blockchain.bitcoin.SelectParams')
    @patch('payment.blockchain.bitcoin.rpc.Proxy')
    def test_init(self, proxy_mock, select_params_mock):
        bc = BlockChain('mainnet')
        self.assertTrue(select_params_mock.called)
        self.assertEqual(select_params_mock.call_args[0][0], 'mainnet')
        self.assertTrue(proxy_mock.called)
        service_url = proxy_mock.call_args[0][0]
        self.assertTrue(service_url.startswith('https'))

    @patch('payment.blockchain.bitcoin.rpc.Proxy')
    def test_get_balance(self, proxy_mock):
        proxy_mock.return_value = Mock(**{
            'getbalance.return_value': 500000,
        })
        bc = BlockChain('mainnet')
        balance = bc.get_balance()
        self.assertEqual(balance, Decimal('0.005'))

    @patch('payment.blockchain.bitcoin.rpc.Proxy')
    def test_get_address_balance(self, proxy_mock):
        proxy_mock.return_value = Mock(**{
            'getreceivedbyaddress.return_value': 500000,
        })
        bc = BlockChain('mainnet')
        balance = bc.get_address_balance('test')
        self.assertEqual(balance, Decimal('0.005'))

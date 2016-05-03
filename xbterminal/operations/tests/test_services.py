from decimal import Decimal
from django.test import TestCase
from mock import patch, Mock

from operations.services import wrappers, blockcypher, sochain


class WrappersTestCase(TestCase):

    @patch('operations.services.wrappers.coindesk.get_exchange_rate')
    @patch('operations.services.wrappers.btcaverage.get_exchange_rate')
    def test_get_exchage_rate(self, btcavg_mock, coindesk_mock):
        coindesk_mock.side_effect = ValueError
        btcavg_mock.return_value = Decimal('200')
        rate = wrappers.get_exchange_rate('USD')
        self.assertEqual(rate, Decimal('200'))

    @patch('operations.services.wrappers.blockcypher.is_tx_reliable')
    @patch('operations.services.wrappers.sochain.is_tx_reliable')
    def test_is_tx_reliable(self, so_mock, bc_mock):
        bc_mock.side_effect = ValueError
        so_mock.return_value = True
        self.assertTrue(wrappers.is_tx_reliable('tx_id', 'mainnet'))


class BlockcypherTestCase(TestCase):

    @patch('operations.services.blockcypher.requests.get')
    def test_is_tx_reliable(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'confirmations': 0,
                'confidence': 0.93,
            },
        })
        tx_id = '0' * 64
        self.assertFalse(blockcypher.is_tx_reliable(tx_id, 'mainnet'))
        args = get_mock.call_args
        self.assertIn('/btc/main/', args[0][0])
        self.assertEqual(args[1]['params']['includeConfidence'], 'true')

    @patch('operations.services.blockcypher.requests.get')
    def test_is_tx_reliable_confirmed(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'confirmations': 1,
                'confidence': 1,
            },
        })
        tx_id = '0' * 64
        self.assertTrue(blockcypher.is_tx_reliable(tx_id, 'mainnet'))
        self.assertIn('/btc/main/', get_mock.call_args[0][0])

    def test_get_tx_url(self):
        tx = 'test'
        self.assertEqual(blockcypher.get_tx_url(tx, 'mainnet'),
                         'https://live.blockcypher.com/btc/tx/test/')

    def test_get_address_url(self):
        address = 'test'
        self.assertEqual(blockcypher.get_address_url(address, 'mainnet'),
                         'https://live.blockcypher.com/btc/address/test/')


class SoChainTestCase(TestCase):

    @patch('operations.services.sochain.requests.get')
    def test_is_tx_reliable(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'data': {
                    'confirmations': 0,
                    'confidence': 0.93,
                },
            },
        })
        tx_id = '0' * 64
        self.assertFalse(sochain.is_tx_reliable(tx_id, 'mainnet'))
        self.assertIn('/BTC/', get_mock.call_args[0][0])

    @patch('operations.services.sochain.requests.get')
    def test_is_tx_reliable_confirmed(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'data': {
                    'confirmations': 1,
                    'confidence': 1,
                },
            },
        })
        tx_id = '0' * 64
        self.assertTrue(sochain.is_tx_reliable(tx_id, 'mainnet'))
        self.assertIn('/BTC/', get_mock.call_args[0][0])

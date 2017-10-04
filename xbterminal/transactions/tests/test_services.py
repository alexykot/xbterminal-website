from decimal import Decimal
from django.test import TestCase
from mock import patch, Mock

from transactions.services import wrappers, blockcypher, sochain


class WrappersTestCase(TestCase):

    @patch('transactions.services.wrappers.coindesk.get_exchange_rate')
    @patch('transactions.services.wrappers.btcaverage.get_exchange_rate')
    def test_get_exchage_rate(self, btcavg_mock, coindesk_mock):
        coindesk_mock.side_effect = ValueError
        btcavg_mock.return_value = Decimal('200')
        rate = wrappers.get_exchange_rate('USD')
        self.assertEqual(rate, Decimal('200'))

    @patch('transactions.services.wrappers.blockcypher.get_tx_confidence')
    @patch('transactions.services.wrappers.sochain.get_tx_confidence')
    def test_is_tx_reliable(self, so_mock, bc_mock):
        bc_mock.side_effect = ValueError
        so_mock.return_value = 0.95
        self.assertIs(
            wrappers.is_tx_reliable('tx_id', 0.9, 'mainnet'), True)

    @patch('transactions.services.wrappers.blockcypher.get_tx_confidence')
    @patch('transactions.services.wrappers.sochain.get_tx_confidence')
    def test_is_tx_reliable_error(self, so_mock, bc_mock):
        bc_mock.side_effect = ValueError
        so_mock.side_effect = ValueError
        self.assertIs(
            wrappers.is_tx_reliable('tx_id', 0.9, 'mainnet'), False)


class BlockcypherTestCase(TestCase):

    @patch('transactions.services.blockcypher.requests.get')
    def test_get_tx_confidence(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'confirmations': 0,
                'confidence': 0.93,
            },
        })
        tx_id = '0' * 64
        self.assertEqual(
            blockcypher.get_tx_confidence(tx_id, 'mainnet'), 0.93)
        args = get_mock.call_args
        self.assertIn('/btc/main/', args[0][0])
        self.assertEqual(args[1]['params']['includeConfidence'], 'true')

    @patch('transactions.services.blockcypher.requests.get')
    def test_get_tx_confidence_confirmed(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'confirmations': 1,
                'confidence': None,
            },
        })
        tx_id = '0' * 64
        self.assertEqual(
            blockcypher.get_tx_confidence(tx_id, 'mainnet'), 1.0)
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

    @patch('transactions.services.sochain.requests.get')
    def test_get_tx_confidence(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'data': {
                    'confirmations': 0,
                    'confidence': 0.93,
                },
            },
        })
        tx_id = '0' * 64
        self.assertEqual(
            sochain.get_tx_confidence(tx_id, 'mainnet'), 0.93)
        self.assertIn('/BTC/', get_mock.call_args[0][0])

    @patch('transactions.services.sochain.requests.get')
    def test_get_tx_confidence_confirmed(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'data': {
                    'confirmations': 1,
                    'confidence': None,
                },
            },
        })
        tx_id = '0' * 64
        self.assertEqual(
            sochain.get_tx_confidence(tx_id, 'mainnet'), 1.0)
        self.assertIn('/BTC/', get_mock.call_args[0][0])

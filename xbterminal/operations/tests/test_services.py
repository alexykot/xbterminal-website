from decimal import Decimal
from django.test import TestCase
from mock import patch, Mock

from operations.services import price, blockcypher


class ExchangeRateTestCase(TestCase):

    @patch('operations.services.price.get_coindesk_rate')
    def test_coindesk(self, coindesk_mock):
        coindesk_mock.return_value = Decimal('200')
        rate = price.get_exchange_rate('USD')
        self.assertEqual(rate, Decimal('200'))


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

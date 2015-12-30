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
            'json.return_value': {'confidence': 0.99},
        })
        tx_id = '0' * 64
        self.assertTrue(blockcypher.is_tx_reliable(tx_id, 'mainnet'))
        self.assertIn('/btc/main/', get_mock.call_args[0][0])

from decimal import Decimal

from django.test import TestCase

from transactions.utils.payments import (
    construct_payment_uri,
    validate_address)


class PaymentUtilsTestCase(TestCase):

    def test_construct_uri_btc(self):
        result = construct_payment_uri(
            'BTC',
            '1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6',
            Decimal('0.125'),
            'test',
            'http://test/req1',
            'http://test/req2')
        self.assertEqual(
            result,
            'bitcoin:1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6?'
            'amount=0.12500000&label=test&message=test&'
            'r=http://test/req1&r1=http://test/req2')

    def test_construct_uri_dash(self):
        result = construct_payment_uri(
            'DASH',
            'Xjoaki4DkHbG7MudD3YhsUPETidufsB8S7',
            Decimal('0.125'),
            'test')
        self.assertEqual(
            result,
            'dash:Xjoaki4DkHbG7MudD3YhsUPETidufsB8S7?'
            'amount=0.12500000&label=test&message=test')

    def test_validate_address_btc(self):
        btc_addr = '1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6'
        self.assertIsNone(
            validate_address(btc_addr, 'BTC'))
        tbtc_addr = 'mxqpfcxzKnPfgZw8JKs7DU6m7DTysxBBWn'
        self.assertIsNone(
            validate_address(tbtc_addr, 'TBTC'))
        self.assertEqual(
            validate_address(tbtc_addr, 'BTC'),
            'Invalid address for coin BTC.')
        invalid_addr = '1wFSdAv9rGpA4CvX3UtxZpUwaumsWM68pC'
        self.assertEqual(
            validate_address(invalid_addr, None),
            'Invalid address.')

    def test_validate_address_dash(self):
        dash_addr = 'Xjoaki4DkHbG7MudD3YhsUPETidufsB8S7'
        self.assertEqual(
            validate_address(dash_addr, 'BTC'),
            'Invalid address for coin BTC.')
        self.assertIsNone(
            validate_address(dash_addr, 'DASH'))
        tdash_addr = 'yfyzM58VsmjfbXtTzNrYH14TmJvY3Nn3Ms'
        self.assertIsNone(
            validate_address(tdash_addr, 'TDASH'))

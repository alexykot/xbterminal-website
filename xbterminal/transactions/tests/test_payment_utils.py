from decimal import Decimal

from django.test import TestCase

from transactions.utils.payments import construct_payment_uri


class TxUtilsTestCase(TestCase):

    def test_btc(self):
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

    def test_dash(self):
        result = construct_payment_uri(
            'DASH',
            'Xjoaki4DkHbG7MudD3YhsUPETidufsB8S7',
            Decimal('0.125'),
            'test')
        self.assertEqual(
            result,
            'dash:Xjoaki4DkHbG7MudD3YhsUPETidufsB8S7?'
            'amount=0.12500000&label=test&message=test')

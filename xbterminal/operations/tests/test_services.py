from decimal import Decimal
from django.test import TestCase
from mock import patch

from operations.services import price


class ExchangeRateTestCase(TestCase):

    @patch('operations.services.price.get_coindesk_rate')
    def test_coindesk(self, coindesk_mock):
        coindesk_mock.return_value = Decimal('200')
        rate = price.get_exchange_rate('USD')
        self.assertEqual(rate, Decimal('200'))

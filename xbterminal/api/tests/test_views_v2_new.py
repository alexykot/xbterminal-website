from django.test import TestCase

from transactions.tests.factories import DepositFactory
from api.views_v2_new import DepositSerializer


class DepositSerializerTestCase(TestCase):

    def test_serialization(self):
        deposit = DepositFactory(received=True)
        data = DepositSerializer(deposit).data
        self.assertEqual(data['uid'], deposit.uid)
        self.assertEqual(data['fiat_amount'].rstrip('0'),
                         str(deposit.amount).rstrip('0'))
        self.assertEqual(data['btc_amount'], str(deposit.coin_amount))
        self.assertEqual(data['paid_btc_amount'],
                         str(deposit.paid_coin_amount))
        self.assertEqual(data['exchange_rate'],
                         str(deposit.effective_exchange_rate))
        self.assertEqual(data['status'], deposit.status)

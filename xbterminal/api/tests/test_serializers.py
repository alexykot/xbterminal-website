from django.test import TestCase

from website.tests.factories import WithdrawalOrderFactory
from api.serializers import WithdrawalOrderSerializer


class WithdrawalFormTestCase(TestCase):

    fixtures = ['initial_data.json']

    def test_serialization(self):
        order = WithdrawalOrderFactory.create()
        data = WithdrawalOrderSerializer(order).data
        self.assertEqual(data['uid'], order.uid)
        self.assertEqual(data['fiat_amount'], str(order.fiat_amount))
        self.assertEqual(data['btc_amount'], str(order.btc_amount))
        self.assertEqual(data['exchange_rate'],
                         str(order.effective_exchange_rate))
        self.assertEqual(data['status'], order.status)

from decimal import Decimal

from django.test import TestCase

from wallet.constants import BIP44_COIN_TYPES
from wallet.tests.factories import AddressFactory
from transactions.models import Deposit
from website.tests.factories import DeviceFactory


class DepositTestCase(TestCase):

    def test_create(self):
        device = DeviceFactory()
        address = AddressFactory()
        deposit = Deposit.objects.create(
            account=device.account,
            device=device,
            currency=device.merchant.currency,
            amount=Decimal('10.0'),
            coin_type=BIP44_COIN_TYPES.BTC,
            merchant_coin_amount=Decimal('0.005'),
            fee_coin_amount=Decimal('0.0001'),
            deposit_address=address)
        self.assertIsNotNone(deposit.uid)
        self.assertEqual(len(deposit.uid), 6)
        self.assertEqual(deposit.paid_coin_amount, 0)
        self.assertIsNone(deposit.refund_address)
        self.assertEqual(len(deposit.incoming_tx_ids), 0)
        self.assertIsNone(deposit.refund_tx_id)
        self.assertIsNone(deposit.payment_type)
        self.assertIsNotNone(deposit.time_created)
        self.assertIsNone(deposit.time_received)
        self.assertIsNone(deposit.time_notified)
        self.assertIsNone(deposit.time_confirmed)
        self.assertIsNone(deposit.time_refunded)
        self.assertIsNone(deposit.time_cancelled)
        self.assertEqual(str(deposit), deposit.uid)

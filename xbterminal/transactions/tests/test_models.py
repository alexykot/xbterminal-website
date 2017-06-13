import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from wallet.constants import BIP44_COIN_TYPES
from wallet.tests.factories import AddressFactory
from transactions.models import Deposit
from transactions.tests.factories import DepositFactory
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
        self.assertEqual(str(deposit), str(deposit.pk))

    def test_factory(self):
        deposit = DepositFactory()
        self.assertIsNotNone(deposit.device)
        self.assertEqual(deposit.account, deposit.device.account)
        self.assertEqual(deposit.currency,
                         deposit.account.merchant.currency)
        self.assertGreater(deposit.amount, 0)
        self.assertEqual(deposit.coin_type, BIP44_COIN_TYPES.BTC)
        self.assertGreater(deposit.merchant_coin_amount, 0)
        self.assertGreater(deposit.fee_coin_amount, 0)
        self.assertEqual(
            deposit.deposit_address.wallet_account.parent_key.coin_type,
            BIP44_COIN_TYPES.BTC)

    def test_factory_exchange_rate(self):
        deposit = DepositFactory(amount=Decimal('10.00'),
                                 exchange_rate=Decimal('2000.00'))
        self.assertEqual(deposit.merchant_coin_amount, Decimal('0.005'))
        self.assertEqual(deposit.fee_coin_amount, Decimal('0.000025'))

    def test_factory_no_device(self):
        deposit = DepositFactory(device=None)
        self.assertIsNone(deposit.device)
        self.assertEqual(deposit.currency,
                         deposit.account.merchant.currency)

    def test_merchant(self):
        deposit = DepositFactory()
        self.assertEqual(deposit.merchant,
                         deposit.account.merchant)

    def test_status(self):
        deposit = DepositFactory()
        self.assertEqual(deposit.status, 'new')
        deposit.paid_coin_amount = deposit.coin_amount / 2
        self.assertEqual(deposit.status, 'underpaid')
        deposit.paid_coin_amount = deposit.coin_amount
        deposit.time_received = timezone.now()
        self.assertEqual(deposit.status, 'received')
        deposit.time_broadcasted = timezone.now()
        self.assertEqual(deposit.status, 'broadcasted')
        deposit.time_notified = timezone.now()
        self.assertEqual(deposit.status, 'notified')
        deposit.time_confirmed = timezone.now()
        self.assertEqual(deposit.status, 'confirmed')

    def test_status_timeout(self):
        deposit = DepositFactory(
            time_created=timezone.now() - datetime.timedelta(minutes=60))
        self.assertEqual(deposit.status, 'timeout')

    def test_status_failed(self):
        deposit = DepositFactory(
            time_created=timezone.now() - datetime.timedelta(minutes=60),
            time_received=timezone.now() - datetime.timedelta(minutes=45))
        self.assertEqual(deposit.status, 'failed')

    def test_status_unconfirmed(self):
        deposit = DepositFactory(
            time_created=timezone.now() - datetime.timedelta(minutes=500),
            time_received=timezone.now() - datetime.timedelta(minutes=490),
            time_notified=timezone.now() - datetime.timedelta(minutes=480))
        self.assertEqual(deposit.status, 'unconfirmed')

    def test_status_refunded(self):
        deposit = DepositFactory(
            time_created=timezone.now() - datetime.timedelta(minutes=120),
            time_received=timezone.now() - datetime.timedelta(minutes=100),
            time_refunded=timezone.now())
        self.assertEqual(deposit.status, 'refunded')

    def test_status_cancelled(self):
        deposit = DepositFactory(
            time_cancelled=timezone.now())
        self.assertEqual(deposit.status, 'cancelled')

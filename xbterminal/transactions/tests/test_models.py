import datetime
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from wallet.constants import BIP44_COIN_TYPES
from wallet.tests.factories import WalletAccountFactory, AddressFactory
from transactions.constants import PAYMENT_TYPES
from transactions.models import (
    Deposit,
    Withdrawal,
    BalanceChange)
from transactions.tests.factories import (
    DepositFactory,
    WithdrawalFactory,
    BalanceChangeFactory)
from website.tests.factories import AccountFactory, DeviceFactory


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
        self.assertEqual(deposit.paid_coin_amount, 0)
        self.assertEqual(
            deposit.deposit_address.wallet_account.parent_key.coin_type,
            BIP44_COIN_TYPES.BTC)
        self.assertIsNone(deposit.refund_address)
        self.assertEqual(len(deposit.incoming_tx_ids), 0)
        self.assertIsNone(deposit.payment_type)
        self.assertEqual(deposit.status, 'new')

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

    def test_factory_received(self):
        deposit = DepositFactory(received=True)
        self.assertEqual(deposit.paid_coin_amount, deposit.coin_amount)
        self.assertIs(deposit.refund_address.startswith('1'), True)
        self.assertEqual(len(deposit.incoming_tx_ids), 1)
        self.assertEqual(len(deposit.incoming_tx_ids[0]), 64)
        self.assertEqual(deposit.payment_type, PAYMENT_TYPES.BIP21)
        self.assertEqual(deposit.status, 'received')

    def test_factory_confirmed(self):
        deposit = DepositFactory(confirmed=True)
        self.assertEqual(deposit.status, 'confirmed')

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

    def test_create_balance_changes(self):
        deposit = DepositFactory(received=True)
        deposit.create_balance_changes()
        changes = list(deposit.balancechange_set.order_by('account'))
        self.assertEqual(len(changes), 2)
        self.assertEqual(changes[0].account, deposit.account)
        self.assertEqual(changes[0].address, deposit.deposit_address)
        self.assertEqual(changes[0].amount,
                         deposit.paid_coin_amount - deposit.fee_coin_amount)
        self.assertIsNone(changes[1].account)
        self.assertEqual(changes[1].address, deposit.deposit_address)
        self.assertEqual(changes[1].amount,
                         deposit.fee_coin_amount)

    def test_create_balance_changes_no_fee(self):
        deposit = DepositFactory(received=True, fee_coin_amount=0)
        deposit.create_balance_changes()
        self.assertEqual(deposit.balancechange_set.count(), 1)
        self.assertEqual(deposit.balancechange_set.get().amount,
                         deposit.paid_coin_amount)


class WithdrawalTestCase(TestCase):

    def test_create(self):
        device = DeviceFactory()
        withdrawal = Withdrawal.objects.create(
            account=device.account,
            device=device,
            currency=device.merchant.currency,
            amount=Decimal('10.0'),
            coin_type=BIP44_COIN_TYPES.BTC,
            customer_coin_amount=Decimal('0.005'),
            tx_fee_coin_amount=Decimal('0.0002'))
        self.assertEqual(len(withdrawal.uid), 6)
        self.assertIsNone(withdrawal.customer_address)
        self.assertIsNone(withdrawal.outgoing_tx_id)
        self.assertIsNotNone(withdrawal.time_created)
        self.assertIsNone(withdrawal.time_sent)
        self.assertIsNone(withdrawal.time_broadcasted)
        self.assertIsNone(withdrawal.time_notified)
        self.assertIsNone(withdrawal.time_confirmed)
        self.assertIsNone(withdrawal.time_cancelled)
        self.assertEqual(str(withdrawal), str(withdrawal.pk))

    def test_factory(self):
        withdrawal = WithdrawalFactory()
        self.assertEqual(withdrawal.device.account, withdrawal.account)
        self.assertEqual(withdrawal.currency,
                         withdrawal.account.merchant.currency)
        self.assertGreater(withdrawal.amount, 0)
        self.assertEqual(withdrawal.coin_type, BIP44_COIN_TYPES.BTC)
        self.assertGreater(withdrawal.customer_coin_amount, 0)
        self.assertEqual(withdrawal.tx_fee_coin_amount, Decimal('0.0005'))
        self.assertIsNone(withdrawal.customer_address)
        self.assertIsNone(withdrawal.outgoing_tx_id)

    def test_factory_exchange_rate(self):
        withdrawal = WithdrawalFactory(amount=Decimal('10.00'),
                                       exchange_rate=Decimal('2000.00'))
        self.assertEqual(withdrawal.customer_coin_amount, Decimal('0.005'))

    def test_factory_no_device(self):
        withdrawal = WithdrawalFactory(device=None)
        self.assertIsNone(withdrawal.device)
        self.assertEqual(withdrawal.currency,
                         withdrawal.account.merchant.currency)

    def test_status(self):
        withdrawal = WithdrawalFactory()
        self.assertEqual(withdrawal.status, 'new')
        withdrawal.time_sent = timezone.now()
        self.assertEqual(withdrawal.status, 'sent')
        withdrawal.time_broadcasted = timezone.now()
        self.assertEqual(withdrawal.status, 'broadcasted')
        withdrawal.time_notified = timezone.now()
        self.assertEqual(withdrawal.status, 'notified')
        withdrawal.time_confirmed = timezone.now()
        self.assertEqual(withdrawal.status, 'confirmed')

    def test_status_timeout(self):
        withdrawal = WithdrawalFactory(
            time_created=timezone.now() - datetime.timedelta(minutes=60))
        self.assertEqual(withdrawal.status, 'timeout')

    def test_status_failed(self):
        withdrawal = WithdrawalFactory(
            time_created=timezone.now() - datetime.timedelta(minutes=60),
            time_sent=timezone.now() - datetime.timedelta(minutes=45))
        self.assertEqual(withdrawal.status, 'failed')

    def test_status_unconfirmed(self):
        withdrawal = WithdrawalFactory(
            time_created=timezone.now() - datetime.timedelta(minutes=500),
            time_sent=timezone.now() - datetime.timedelta(minutes=490),
            time_broadcasted=timezone.now() - datetime.timedelta(minutes=480),
            time_notified=timezone.now() - datetime.timedelta(minutes=480))
        self.assertEqual(withdrawal.status, 'unconfirmed')

    def test_status_cancelled(self):
        withdrawal = WithdrawalFactory(
            time_cancelled=timezone.now())
        self.assertEqual(withdrawal.status, 'cancelled')


class BalanceChangeTestCase(TestCase):

    def test_create(self):
        deposit = DepositFactory()
        change = BalanceChange.objects.create(
            deposit=deposit,
            account=deposit.account,
            address=deposit.deposit_address,
            amount=deposit.paid_coin_amount - deposit.fee_coin_amount)
        self.assertIsNone(change.withdrawal)
        self.assertEqual(str(change), str(change.pk))
        self.assertEqual(deposit.balancechange_set.count(), 1)
        self.assertEqual(deposit.account.balancechange_set.count(), 1)
        self.assertEqual(deposit.deposit_address.balancechange_set.count(), 1)

    def test_factory(self):
        change = BalanceChangeFactory()
        self.assertIsNotNone(change.deposit)
        self.assertIsNone(change.withdrawal)
        self.assertEqual(change.deposit.status, 'received')
        self.assertEqual(change.account, change.deposit.account)
        self.assertEqual(change.address, change.deposit.deposit_address)
        self.assertEqual(change.amount, change.deposit.paid_coin_amount)

    def test_deposit_and_withdrawal(self):
        deposit = DepositFactory()
        withdrawal = WithdrawalFactory()
        with self.assertRaises(IntegrityError):
            BalanceChange.objects.create(
                deposit=deposit,
                withdrawal=withdrawal,
                account=deposit.account,
                address=deposit.deposit_address,
                amount=deposit.paid_coin_amount)

    def test_no_deposit_no_withdrawal(self):
        account = AccountFactory()
        address = AddressFactory()
        with self.assertRaises(IntegrityError):
            BalanceChange.objects.create(
                account=account,
                address=address,
                amount=Decimal('10.00'))

    def test_exclude_unconfirmed(self):
        wallet_account = WalletAccountFactory()
        change_1 = BalanceChangeFactory(
            deposit__deposit_address__wallet_account=wallet_account)
        change_2 = BalanceChangeFactory(
            deposit__deposit_address__wallet_account=wallet_account,
            deposit__confirmed=True)
        self.assertIn(change_1, BalanceChange.objects.all())
        self.assertNotIn(change_1, BalanceChange.objects.exclude_unconfirmed())
        self.assertIn(change_2, BalanceChange.objects.all())
        self.assertIn(change_2, BalanceChange.objects.exclude_unconfirmed())

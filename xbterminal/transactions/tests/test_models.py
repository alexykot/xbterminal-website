import datetime
from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from wallet.constants import BIP44_COIN_TYPES
from wallet.tests.factories import AddressFactory
from transactions.constants import PAYMENT_TYPES
from transactions.models import (
    Deposit,
    Withdrawal,
    BalanceChange)
from transactions.tests.factories import (
    DepositFactory,
    WithdrawalFactory,
    BalanceChangeFactory,
    NegativeBalanceChangeFactory)
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
        self.assertEqual(deposit.refund_coin_amount, 0)
        self.assertIsNone(deposit.refund_address)
        self.assertEqual(len(deposit.incoming_tx_ids), 0)
        self.assertIsNone(deposit.refund_tx_id)
        self.assertIsNone(deposit.payment_type)
        self.assertIsNotNone(deposit.time_created)
        self.assertIsNone(deposit.time_received)
        self.assertIsNone(deposit.time_notified)
        self.assertIsNone(deposit.time_confirmed)
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
        self.assertEqual(deposit.refund_coin_amount, 0)
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
        self.assertEqual(deposit.exchange_rate, Decimal('2000.00'))

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

    def test_factory_broadcasted(self):
        deposit = DepositFactory(broadcasted=True)
        self.assertEqual(deposit.status, 'broadcasted')

    def test_factory_notified(self):
        deposit = DepositFactory(notified=True)
        self.assertEqual(deposit.status, 'notified')

    def test_factory_confirmed(self):
        deposit = DepositFactory(confirmed=True)
        self.assertEqual(deposit.status, 'confirmed')

    def test_factory_timeout(self):
        deposit = DepositFactory(timeout=True)
        self.assertEqual(deposit.status, 'timeout')

    def test_factory_failed(self):
        deposit = DepositFactory(failed=True)
        self.assertEqual(deposit.status, 'failed')

    def test_factory_unconfirmed(self):
        deposit = DepositFactory(unconfirmed=True)
        self.assertEqual(deposit.status, 'unconfirmed')

    def test_factory_refunded(self):
        deposit = DepositFactory(refunded=True)
        self.assertEqual(deposit.refund_coin_amount, deposit.paid_coin_amount)
        self.assertIsNotNone(deposit.refund_address)
        self.assertIsNotNone(deposit.refund_tx_id)
        self.assertEqual(deposit.status, 'failed')

    def test_factory_cancelled(self):
        deposit = DepositFactory(cancelled=True)
        self.assertEqual(deposit.status, 'cancelled')

    def test_merchant(self):
        deposit = DepositFactory()
        self.assertEqual(deposit.merchant,
                         deposit.account.merchant)

    def test_exchange_rate(self):
        deposit = DepositFactory(
            amount=Decimal('10.0'),
            merchant_coin_amount=Decimal('0.01'),
            fee_coin_amount=Decimal('0.0005'))
        self.assertEqual(deposit.exchange_rate, Decimal('1000.00'))
        self.assertEqual(deposit.effective_exchange_rate,
                         Decimal('952.38095238'))

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

    def test_status_cancelled(self):
        deposit = DepositFactory(
            time_cancelled=timezone.now())
        self.assertEqual(deposit.status, 'cancelled')

    def test_receipt_url(self):
        deposit = DepositFactory(notified=True)
        self.assertIn('/prc/{0}'.format(deposit.uid), deposit.receipt_url)

    def test_create_payment_request(self):
        deposit = DepositFactory()
        response_url = 'http://some-url'
        payment_request = deposit.create_payment_request(response_url)
        self.assertIs(isinstance(payment_request, bytes), True)
        self.assertGreater(len(payment_request), 0)

    def test_create_balance_changes(self):
        deposit = DepositFactory(received=True)
        deposit.create_balance_changes()
        changes = list(deposit.balancechange_set.order_by('created_at'))
        self.assertEqual(len(changes), 2)
        self.assertEqual(changes[0].account, deposit.account)
        self.assertEqual(changes[0].address, deposit.deposit_address)
        self.assertEqual(changes[0].amount,
                         deposit.paid_coin_amount - deposit.fee_coin_amount)
        self.assertIsNone(changes[1].account)
        self.assertEqual(changes[1].address, deposit.deposit_address)
        self.assertEqual(changes[1].amount,
                         deposit.fee_coin_amount)

    def test_create_balance_changes_repeat(self):
        deposit = DepositFactory(received=True)
        deposit.create_balance_changes()
        deposit.paid_coin_amount *= 2
        deposit.save()
        deposit.create_balance_changes()
        changes = list(deposit.balancechange_set.order_by('created_at'))
        self.assertEqual(len(changes), 2)
        self.assertEqual(changes[0].account, deposit.account)
        self.assertEqual(changes[0].amount,
                         deposit.paid_coin_amount - deposit.fee_coin_amount)
        self.assertIsNone(changes[1].account)
        self.assertEqual(changes[1].amount,
                         deposit.fee_coin_amount)

    def test_create_balance_changes_no_fee(self):
        deposit = DepositFactory(received=True, fee_coin_amount=0)
        deposit.create_balance_changes()
        self.assertEqual(deposit.balancechange_set.count(), 1)
        self.assertEqual(deposit.balancechange_set.get().amount,
                         deposit.paid_coin_amount)

    def test_create_balance_changes_refund(self):
        deposit = DepositFactory(refunded=True)
        deposit.create_balance_changes()
        changes = list(deposit.balancechange_set.order_by('created_at'))
        self.assertEqual(len(changes), 0)

    def test_create_balance_changes_partial_refund(self):
        deposit = DepositFactory(
            refunded=True,
            merchant_coin_amount=Decimal('0.010'),
            fee_coin_amount=Decimal('0.001'),
            paid_coin_amount=Decimal('0.015'),
            refund_coin_amount=Decimal('0.004'))
        deposit.create_balance_changes()
        changes = list(deposit.balancechange_set.order_by('created_at'))
        self.assertEqual(len(changes), 3)
        self.assertEqual(changes[2].account, deposit.account)
        self.assertEqual(changes[2].address, deposit.deposit_address)
        self.assertEqual(changes[2].amount, -deposit.refund_coin_amount)


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

    def test_factory_sent(self):
        withdrawal = WithdrawalFactory(sent=True)
        self.assertIs(withdrawal.customer_address.startswith('1'), True)
        self.assertEqual(len(withdrawal.outgoing_tx_id), 64)
        self.assertEqual(withdrawal.status, 'sent')

    def test_factory_broadcasted(self):
        withdrawal = WithdrawalFactory(broadcasted=True)
        self.assertEqual(withdrawal.status, 'broadcasted')

    def test_factory_notified(self):
        withdrawal = WithdrawalFactory(notified=True)
        self.assertEqual(withdrawal.status, 'notified')

    def test_factory_confirmed(self):
        withdrawal = WithdrawalFactory(confirmed=True)
        self.assertEqual(withdrawal.status, 'confirmed')

    def test_factory_timeout(self):
        withdrawal = WithdrawalFactory(timeout=True)
        self.assertEqual(withdrawal.status, 'timeout')

    def test_factory_failed(self):
        withdrawal = WithdrawalFactory(failed=True)
        self.assertEqual(withdrawal.status, 'failed')

    def test_factory_unconfirmed(self):
        withdrawal = WithdrawalFactory(unconfirmed=True)
        self.assertEqual(withdrawal.status, 'unconfirmed')

    def test_factory_cancelled(self):
        withdrawal = WithdrawalFactory(cancelled=True)
        self.assertEqual(withdrawal.status, 'cancelled')

    def test_exchange_rate(self):
        withdrawal = WithdrawalFactory(
            amount=Decimal('10.0'),
            customer_coin_amount=Decimal('0.01'),
            tx_fee_coin_amount=Decimal('0.0005'))
        self.assertEqual(withdrawal.exchange_rate, Decimal('1000.00'))
        self.assertEqual(withdrawal.effective_exchange_rate,
                         Decimal('952.38095238'))

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
        bch = BalanceChange.objects.create(
            deposit=deposit,
            account=deposit.account,
            address=deposit.deposit_address,
            amount=deposit.paid_coin_amount - deposit.fee_coin_amount)
        self.assertIsNone(bch.withdrawal)
        self.assertIsNotNone(bch.created_at)
        self.assertEqual(str(bch), str(bch.pk))
        self.assertEqual(deposit.balancechange_set.count(), 1)
        self.assertEqual(deposit.account.balancechange_set.count(), 1)
        self.assertEqual(deposit.deposit_address.balancechange_set.count(), 1)

    def test_factory_positive(self):
        bch = BalanceChangeFactory()
        self.assertIsNotNone(bch.deposit)
        self.assertIsNone(bch.withdrawal)
        self.assertEqual(bch.account, bch.deposit.account)
        self.assertEqual(bch.address, bch.deposit.deposit_address)
        self.assertEqual(bch.amount, bch.deposit.merchant_coin_amount)
        self.assertEqual(bch.amount, bch.deposit.paid_coin_amount)
        self.assertEqual(bch.deposit.fee_coin_amount, 0)
        self.assertEqual(bch.deposit.status, 'received')

    def test_factory_negative(self):
        bch = NegativeBalanceChangeFactory()
        self.assertIsNone(bch.deposit)
        self.assertIsNotNone(bch.withdrawal)
        self.assertEqual(bch.account, bch.withdrawal.account)
        self.assertEqual(bch.amount, -bch.withdrawal.coin_amount)
        self.assertEqual(bch.withdrawal.tx_fee_coin_amount, 0)
        self.assertEqual(bch.withdrawal.status, 'sent')

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
        bch_1 = BalanceChangeFactory()
        bch_2 = BalanceChangeFactory(deposit__confirmed=True)
        bch_3 = NegativeBalanceChangeFactory()
        self.assertIn(bch_1, BalanceChange.objects.all())
        self.assertNotIn(bch_1, BalanceChange.objects.exclude_unconfirmed())
        self.assertIn(bch_2, BalanceChange.objects.all())
        self.assertIn(bch_2, BalanceChange.objects.exclude_unconfirmed())
        self.assertIn(bch_3, BalanceChange.objects.all())
        self.assertIn(bch_3, BalanceChange.objects.exclude_unconfirmed())

    def test_is_confirmed(self):
        bch_1 = BalanceChangeFactory()
        self.assertIs(bch_1.is_confirmed(), False)
        bch_2 = BalanceChangeFactory(deposit__confirmed=True)
        self.assertIs(bch_2.is_confirmed(), True)
        bch_3 = NegativeBalanceChangeFactory()
        self.assertIs(bch_3.is_confirmed(), True)
        bch_4 = NegativeBalanceChangeFactory(
            address__is_change=True,
            amount=Decimal('0.01'))
        self.assertIs(bch_4.is_confirmed(), False)
        bch_5 = NegativeBalanceChangeFactory(
            withdrawal__confirmed=True,
            address__is_change=True,
            amount=Decimal('0.01'))
        self.assertIs(bch_5.is_confirmed(), True)

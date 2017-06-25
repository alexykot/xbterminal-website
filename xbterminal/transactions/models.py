from __future__ import unicode_literals

from django.contrib.postgres.fields import ArrayField
from django.db import models, IntegrityError
from django.db.transaction import atomic
from django.utils import timezone

from common.uids import generate_b58_uid
from wallet.constants import BIP44_COIN_TYPES
from transactions.constants import (
    BTC_DEC_PLACES,
    DEPOSIT_TIMEOUT,
    DEPOSIT_CONFIDENCE_TIMEOUT,
    DEPOSIT_CONFIRMATION_TIMEOUT,
    WITHDRAWAL_TIMEOUT,
    WITHDRAWAL_CONFIDENCE_TIMEOUT,
    WITHDRAWAL_CONFIRMATION_TIMEOUT,
    PAYMENT_TYPES)


class Transaction(models.Model):
    """
    Base model for Deposit and Withdrawal
    """
    uid = models.CharField(
        'UID',
        max_length=6,
        editable=False,
        unique=True)
    account = models.ForeignKey(
        'website.Account',
        on_delete=models.PROTECT)
    device = models.ForeignKey(
        'website.Device',
        on_delete=models.SET_NULL,
        null=True)

    currency = models.ForeignKey(
        'website.Currency',
        on_delete=models.PROTECT)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2)

    coin_type = models.PositiveSmallIntegerField(
        choices=BIP44_COIN_TYPES)

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.pk)

    @property
    def merchant(self):
        return self.account.merchant

    @property
    def bitcoin_network(self):
        return get_bitcoin_network(self.coin_type)


class Deposit(Transaction):

    merchant_coin_amount = models.DecimalField(
        max_digits=18,
        decimal_places=8)
    fee_coin_amount = models.DecimalField(
        max_digits=18,
        decimal_places=8)
    paid_coin_amount = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        default=0)

    deposit_address = models.OneToOneField(
        'wallet.Address',
        on_delete=models.PROTECT)
    refund_address = models.CharField(
        max_length=35,
        null=True)

    incoming_tx_ids = ArrayField(
        models.CharField(max_length=64),
        default=list)
    refund_tx_id = models.CharField(
        max_length=64,
        null=True)
    payment_type = models.PositiveSmallIntegerField(
        choices=PAYMENT_TYPES,
        null=True)

    time_created = models.DateTimeField(auto_now_add=True)
    time_received = models.DateTimeField(null=True)
    time_broadcasted = models.DateTimeField(null=True)
    time_notified = models.DateTimeField(null=True)
    time_confirmed = models.DateTimeField(null=True)
    time_refunded = models.DateTimeField(null=True)
    time_cancelled = models.DateTimeField(null=True)

    @property
    def exchange_rate(self):
        return (self.amount /
                self.merchant_coin_amount).quantize(BTC_DEC_PLACES)

    @property
    def coin_amount(self):
        """
        Total BTC amount (for payment)
        """
        return self.merchant_coin_amount + self.fee_coin_amount

    @property
    def status(self):
        """
        Returns status of the deposit:
            new - deposit has just been created
            underpaid - incoming transaction received,
                but amount is not sufficient
            received - incoming transaction received, full amount
            broadcasted: all incoming transactions are
                reached the confidence threshold
            notified - customer notified about successful payment
            confirmed - incoming transaction confirmed
            refunded - money sent back to customer
            timeout - incoming transaction did not received
            failed - incoming transaction received,
                but payment order is not marked as notified
            unconfirmed - customer notified about successful payment,
                but incoming transaction is not confirmed
            cancelled: deposit cancelled by the customer
        """
        if self.time_refunded:
            return 'refunded'
        if self.time_cancelled:
            return 'cancelled'
        if self.time_notified:
            if self.time_confirmed:
                return 'confirmed'
            else:
                if self.time_created + DEPOSIT_CONFIRMATION_TIMEOUT < timezone.now():
                    return 'unconfirmed'
                else:
                    return 'notified'
        if self.time_received:
            if self.time_created + DEPOSIT_CONFIDENCE_TIMEOUT < timezone.now():
                return 'failed'
            elif self.time_broadcasted:
                return 'broadcasted'
            else:
                return 'received'
        else:
            if self.time_created + DEPOSIT_TIMEOUT < timezone.now():
                return 'timeout'
            else:
                if 0 < self.paid_coin_amount < self.coin_amount:
                    return 'underpaid'
                else:
                    return 'new'

    @atomic
    def create_balance_changes(self):
        self.balancechange_set.all().delete()
        self.balancechange_set.create(
            account=self.account,
            address=self.deposit_address,
            amount=self.paid_coin_amount - self.fee_coin_amount)
        if self.fee_coin_amount > 0:
            self.balancechange_set.create(
                account=None,
                address=self.deposit_address,
                amount=self.fee_coin_amount)

    @atomic
    def save(self, *args, **kwargs):
        if not self.pk:
            while True:
                uid = generate_b58_uid(6)
                if not Deposit.objects.filter(uid=uid).exists():
                    self.uid = uid
                    break
        super(Deposit, self).save(*args, **kwargs)


class Withdrawal(Transaction):

    customer_coin_amount = models.DecimalField(
        max_digits=18,
        decimal_places=8)
    tx_fee_coin_amount = models.DecimalField(
        max_digits=18,
        decimal_places=8)

    customer_address = models.CharField(
        max_length=35,
        null=True)
    outgoing_tx_id = models.CharField(
        max_length=64,
        null=True)

    time_created = models.DateTimeField(auto_now_add=True)
    time_sent = models.DateTimeField(null=True)
    time_broadcasted = models.DateTimeField(null=True)
    time_notified = models.DateTimeField(null=True)
    time_confirmed = models.DateTimeField(null=True)
    time_cancelled = models.DateTimeField(null=True)

    @property
    def exchange_rate(self):
        return (self.amount /
                self.customer_coin_amount).quantize(BTC_DEC_PLACES)

    @property
    def coin_amount(self):
        """
        Total BTC amount (for receipts)
        """
        return self.customer_coin_amount + self.tx_fee_coin_amount

    @property
    def status(self):
        """
        Returns status of the withdrawal:
            new - withdrawal has just been created
            sent - transaction has been sent
            broadcasted: outgoing transaction has reached confidence threshold
            notified: customer notified about successful withdrawal
            confirmed - outgoing transaction confirmed
            timeout - transaction has not been sent
            failed - transaction has been sent,
                but withdrawal is not marked as notified
            unconfirmed - customer notified about successful withdrawal,
                but outgoing transaction is not confirmed
            cancelled: withdrawal cancelled by the customer
        """
        if self.time_notified:
            if self.time_confirmed:
                return 'confirmed'
            else:
                if self.time_created + WITHDRAWAL_CONFIRMATION_TIMEOUT < timezone.now():
                    return 'unconfirmed'
                else:
                    return 'notified'
        if self.time_cancelled:
            return 'cancelled'
        if self.time_sent:
            if self.time_created + WITHDRAWAL_CONFIDENCE_TIMEOUT < timezone.now():
                return 'failed'
            else:
                if self.time_broadcasted:
                    return 'broadcasted'
                else:
                    return 'sent'
        else:
            if self.time_created + WITHDRAWAL_TIMEOUT < timezone.now():
                return 'timeout'
            else:
                return 'new'

    @atomic
    def save(self, *args, **kwargs):
        if not self.pk:
            while True:
                uid = generate_b58_uid(6)
                if not Withdrawal.objects.filter(uid=uid).exists():
                    self.uid = uid
                    break
        super(Withdrawal, self).save(*args, **kwargs)


class BalanceChangeManager(models.Manager):

    def exclude_unconfirmed(self):
        queryset = self.get_queryset()
        return queryset.\
            exclude(
                deposit__isnull=False,
                deposit__time_confirmed__isnull=True).\
            exclude(
                withdrawal__isnull=False,
                withdrawal__time_confirmed__isnull=True,
                amount__gt=0)


class BalanceChange(models.Model):
    """
    Represents balance change on merchant account and/or wallet address
    """
    deposit = models.ForeignKey(
        Deposit,
        on_delete=models.PROTECT,
        null=True)
    withdrawal = models.ForeignKey(
        Withdrawal,
        on_delete=models.PROTECT,
        null=True)

    account = models.ForeignKey(
        'website.Account',
        on_delete=models.PROTECT,
        null=True)
    address = models.ForeignKey(
        'wallet.Address',
        on_delete=models.PROTECT)
    amount = models.DecimalField(
        max_digits=18,
        decimal_places=8)

    objects = BalanceChangeManager()

    def __str__(self):
        return str(self.pk)

    def is_confirmed(self):
        """
        If true, transaction will be included in calculation of
        confirmed balance of the account/address
        """
        if self.deposit:
            return self.deposit.time_confirmed is not None
        elif self.withdrawal:
            # Always include negative balance changes
            return (self.amount < 0 or
                    self.withdrawal.time_confirmed is not None)

    is_confirmed.boolean = True

    def save(self, *args, **kwargs):
        # Deposit or withdrawal, but not both
        if not (self.deposit or self.withdrawal) or \
                (self.deposit and self.withdrawal):
            raise IntegrityError
        super(BalanceChange, self).save(*args, **kwargs)

#
# Compatibility helpers
#


def get_bitcoin_network(coin_type):
    # TODO: use coin types instead in BlokcChain class
    if coin_type == BIP44_COIN_TYPES.BTC:
        network = 'mainnet'
    elif coin_type == BIP44_COIN_TYPES.XTN:
        network = 'testnet'
    else:
        raise ValueError('Invalid coin type')
    return network


def get_coin_type(currency_name):
    """
    Determine coin type from currency name
    """
    if currency_name == 'BTC':
        return BIP44_COIN_TYPES.BTC
    elif currency_name == 'TBTC':
        return BIP44_COIN_TYPES.XTN
    else:
        raise ValueError('Fiat currencies are not supported')


def get_account_balance(account,
                        include_unconfirmed=True,
                        include_offchain=True):
    """
    Return total balance on account
    Accepts:
        account: Account instance
        include_unconfirmed: include unconfirmed changes, bool
        include_offchain: include reserved amounts
    """
    # TODO: replace old balance property
    if not include_unconfirmed:
        changes = account.balancechange_set.exclude_unconfirmed()
    else:
        changes = account.balancechange_set.all()
    if not include_offchain:
        changes = changes.exclude(withdrawal__isnull=False,
                                  withdrawal__time_sent__isnull=True)
    result = changes.aggregate(models.Sum('amount'))
    return result['amount__sum'] or BTC_DEC_PLACES


def get_fee_account_balance(coin_type,
                            include_unconfirmed=True,
                            include_offchain=True):
    """
    Return total collected fees
    """
    if not include_unconfirmed:
        changes = BalanceChange.objects.exclude_unconfirmed()
    else:
        changes = BalanceChange.objects.all()
    if not include_offchain:
        changes = changes.exclude(withdrawal__isnull=False,
                                  withdrawal__time_sent__isnull=True)
    result = changes.\
        filter(address__wallet_account__parent_key__coin_type=coin_type).\
        filter(account__isnull=True).\
        aggregate(models.Sum('amount'))
    return result['amount__sum'] or BTC_DEC_PLACES


def get_address_balance(address, include_unconfirmed=True):
    """
    Return total balance on address
    Accepts:
        account: Account instance
        only_confirmed: whether to exclude unconfirmed changes, bool
    """
    if not include_unconfirmed:
        changes = address.balancechange_set.exclude_unconfirmed()
    else:
        changes = address.balancechange_set.all()
    result = changes.aggregate(models.Sum('amount'))
    return result['amount__sum'] or BTC_DEC_PLACES

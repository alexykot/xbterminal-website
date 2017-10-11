from __future__ import unicode_literals

from django.contrib.postgres.fields import ArrayField
from django.db import models, IntegrityError
from django.db.transaction import atomic
from django.utils import timezone

from api.utils.urls import construct_absolute_url
from common.uids import generate_b58_uid
from transactions.constants import (
    BTC_DEC_PLACES,
    DEPOSIT_TIMEOUT,
    DEPOSIT_CONFIDENCE_TIMEOUT,
    DEPOSIT_CONFIRMATION_TIMEOUT,
    WITHDRAWAL_TIMEOUT,
    WITHDRAWAL_CONFIDENCE_TIMEOUT,
    WITHDRAWAL_CONFIRMATION_TIMEOUT,
    PAYMENT_TYPES)
from transactions.utils.bip70 import create_payment_request
from transactions.utils.compat import get_coin_type


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
        verbose_name='Display currency',
        on_delete=models.PROTECT,
        related_name='+')
    amount = models.DecimalField(
        verbose_name='Display amount',
        max_digits=12,
        decimal_places=2)

    coin = models.ForeignKey(
        'website.Currency',
        on_delete=models.PROTECT,
        limit_choices_to={'is_fiat': False},
        related_name='+',
        help_text='Crypto currency used for transaction processing.')

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.pk)

    @property
    def merchant(self):
        return self.account.merchant

    @property
    def coin_type(self):
        return get_coin_type(self.coin.name)


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
    refund_coin_amount = models.DecimalField(
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
    time_cancelled = models.DateTimeField(null=True)

    @property
    def coin_amount(self):
        """
        Total BTC amount (for payment)
        """
        return self.merchant_coin_amount + self.fee_coin_amount

    @property
    def exchange_rate(self):
        return (self.amount /
                self.merchant_coin_amount).quantize(BTC_DEC_PLACES)

    @property
    def effective_exchange_rate(self):
        """
        For receipts
        """
        return (self.amount / self.coin_amount).quantize(BTC_DEC_PLACES)

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
            timeout - incoming transaction did not received
            failed - incoming transaction received,
                but payment order is not marked as notified
            unconfirmed - customer notified about successful payment,
                but incoming transaction is not confirmed
            cancelled: deposit cancelled by the customer
        """
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

    @property
    def receipt_url(self):
        return construct_absolute_url(
            'api:short:deposit-receipt',
            kwargs={'uid': self.uid})

    def create_payment_request(self, response_url):
        return create_payment_request(
            self.coin.name,
            [(self.deposit_address.address, self.coin_amount)],
            self.time_created,
            self.time_created + DEPOSIT_TIMEOUT,
            response_url,
            self.merchant.company_name)

    @atomic
    def create_balance_changes(self):
        if self.refund_coin_amount == self.paid_coin_amount:
            # Full refund, delete balance changes
            self.balancechange_set.all().delete()
            return
        self.balancechange_set.update_or_create(
            account=self.account,
            address=self.deposit_address,
            amount__gt=0,
            defaults={
                'amount': self.paid_coin_amount - self.fee_coin_amount,
            })
        if self.fee_coin_amount > 0:
            self.balancechange_set.update_or_create(
                account__isnull=True,
                address=self.deposit_address,
                amount__gt=0,
                defaults={
                    'amount': self.fee_coin_amount,
                })
        if self.refund_coin_amount > 0:
            # Partial refund
            if self.refund_coin_amount != self.paid_coin_amount - self.coin_amount:
                raise ValueError
            self.balancechange_set.update_or_create(
                account=self.account,
                address=self.deposit_address,
                amount__lt=0,
                defaults={
                    'amount': -self.refund_coin_amount,
                })

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
    def coin_amount(self):
        """
        Total BTC amount (for receipts)
        """
        return self.customer_coin_amount + self.tx_fee_coin_amount

    @property
    def exchange_rate(self):
        return (self.amount /
                self.customer_coin_amount).quantize(BTC_DEC_PLACES)

    @property
    def effective_exchange_rate(self):
        """
        For receipts
        """
        return (self.amount / self.coin_amount).quantize(BTC_DEC_PLACES)

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
    created_at = models.DateTimeField(
        auto_now_add=True)

    objects = BalanceChangeManager()

    def __str__(self):
        return str(self.pk)

    @property
    def change_type(self):
        if self.deposit:
            if self.amount > 0:
                if self.account:
                    return 'deposit'
                else:
                    return 'deposit fee'
            else:
                return 'deposit refund'
        elif self.withdrawal:
            if self.amount < 0:
                return 'withdrawal'
            else:
                return 'withdrawal change'

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

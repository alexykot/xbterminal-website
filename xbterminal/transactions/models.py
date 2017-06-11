from __future__ import unicode_literals

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.transaction import atomic
from django.utils import timezone

from common.uids import generate_b58_uid
from wallet.constants import BIP44_COIN_TYPES
from transactions.constants import (
    BTC_DEC_PLACES,
    DEPOSIT_TIMEOUT,
    DEPOSIT_VALIDATION_TIMEOUT,
    DEPOSIT_CONFIRMATION_TIMEOUT,
    PAYMENT_TYPES)


class Deposit(models.Model):

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
    time_notified = models.DateTimeField(null=True)
    time_confirmed = models.DateTimeField(null=True)
    time_refunded = models.DateTimeField(null=True)
    time_cancelled = models.DateTimeField(null=True)

    def __str__(self):
        return str(self.pk)

    @property
    def merchant(self):
        return self.account.merchant

    @property
    def bitcoin_network(self):
        # Property for backwards compatibility
        # TODO: use coin types instead
        if self.coin_type == BIP44_COIN_TYPES.BTC:
            network = 'mainnet'
        elif self.coin_type == BIP44_COIN_TYPES.XTN:
            network = 'testnet'
        else:
            raise ValueError('Invalid coin type.')
        return network

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
        if not self.time_received:
            if self.time_created + DEPOSIT_TIMEOUT < timezone.now():
                return 'timeout'
            else:
                if 0 < self.paid_coin_amount < self.coin_amount:
                    return 'underpaid'
                else:
                    return 'new'
        else:
            if self.time_created + DEPOSIT_VALIDATION_TIMEOUT < timezone.now():
                return 'failed'
            else:
                return 'received'

    @atomic
    def save(self, *args, **kwargs):
        if not self.pk:
            while True:
                uid = generate_b58_uid(6)
                if not Deposit.objects.filter(uid=uid).exists():
                    self.uid = uid
                    break
        super(Deposit, self).save(*args, **kwargs)

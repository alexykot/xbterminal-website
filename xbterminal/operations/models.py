import uuid

from bitcoin import base58

from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from website.models import BITCOIN_NETWORKS
from website.validators import (
    validate_bitcoin_address,
    validate_transaction)

from operations import (
    BTC_DEC_PLACES,
    PAYMENT_TIMEOUT,
    PAYMENT_VALIDATION_TIMEOUT,
    PAYMENT_CONFIRMATION_TIMEOUT,
    WITHDRAWAL_TIMEOUT,
    WITHDRAWAL_BROADCAST_TIMEOUT,
    WITHDRAWAL_CONFIRMATION_TIMEOUT)
from operations.protocol import create_payment_request
from api.utils.urls import construct_absolute_url


def gen_payment_uid():
    bts = uuid.uuid4().bytes
    return base58.encode(bts)[:6]


class PaymentOrder(models.Model):

    order_type = 'payment'

    PAYMENT_TYPES = [
        ('bip0021', _('BIP 0021 (Bitcoin URI)')),
        ('bip0070', _('BIP 0070 (Payment Protocol)')),
    ]

    uid = models.CharField('UID',
                           max_length=32,
                           editable=False,
                           unique=True,
                           default=gen_payment_uid)
    device = models.ForeignKey(
        'website.Device',
        on_delete=models.SET_NULL,
        null=True)
    # TODO: this field should be mandatory
    account = models.ForeignKey('website.Account', null=True)

    bitcoin_network = models.CharField(
        max_length=10, choices=BITCOIN_NETWORKS)
    local_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address])
    merchant_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address], null=True)
    fee_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address])
    instantfiat_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address], null=True)
    refund_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address], null=True)
    fiat_currency = models.ForeignKey('website.Currency')
    fiat_amount = models.DecimalField(
        max_digits=12, decimal_places=2)
    instantfiat_fiat_amount = models.DecimalField(
        max_digits=9, decimal_places=2)
    instantfiat_btc_amount = models.DecimalField(
        max_digits=18, decimal_places=8)
    merchant_btc_amount = models.DecimalField(
        max_digits=18, decimal_places=8)
    fee_btc_amount = models.DecimalField(
        max_digits=18, decimal_places=8)
    tx_fee_btc_amount = models.DecimalField(
        max_digits=18, decimal_places=8)
    paid_btc_amount = models.DecimalField(
        max_digits=18, decimal_places=8, default=0)
    extra_btc_amount = models.DecimalField(
        max_digits=18, decimal_places=8, default=0)
    instantfiat_invoice_id = models.CharField(
        max_length=255, null=True)

    incoming_tx_ids = ArrayField(
        models.CharField(max_length=64, validators=[validate_transaction]),
        default=list)
    outgoing_tx_id = models.CharField(
        max_length=64,
        validators=[validate_transaction],
        null=True)
    refund_tx_id = models.CharField(
        max_length=64, validators=[validate_transaction], null=True)
    payment_type = models.CharField(
        max_length=10, choices=PAYMENT_TYPES)

    time_created = models.DateTimeField(auto_now_add=True)
    time_received = models.DateTimeField(null=True)
    time_forwarded = models.DateTimeField(null=True)
    time_exchanged = models.DateTimeField(null=True)
    time_notified = models.DateTimeField(null=True)
    time_confirmed = models.DateTimeField(null=True)
    time_refunded = models.DateTimeField(null=True)
    time_cancelled = models.DateTimeField(null=True)

    def __unicode__(self):
        return self.uid

    @property
    def merchant(self):
        if self.account:
            return self.account.merchant
        else:
            return self.device.merchant

    @property
    def expires_at(self):
        return self.time_created + PAYMENT_TIMEOUT

    @property
    def status(self):
        """
        Returns status of the payment:
            new - payment order has just been created
            underpaid - incoming transaction received,
                but amount is not sufficient
            received - incoming transaction received, full amount
            forwarded - payment forwarded
            processed - received confirmation from instantfiat service
            notified - customer notified about successful payment
            confirmed - outgoing transaction confirmed
            refunded - payment sent back to customer
            timeout - incoming transaction did not received
            failed - incoming transaction received,
                but payment order is not marked as notified
            unconfirmed - customer notified about successful payment,
                but outgoing transaction is not confirmed
            cancelled: payment cancelled by the customer
        """
        if self.time_refunded:
            return 'refunded'
        if self.time_cancelled:
            return 'cancelled'
        if self.time_notified:
            if self.time_confirmed:
                return 'confirmed'
            else:
                if self.time_created + PAYMENT_CONFIRMATION_TIMEOUT < timezone.now():
                    return 'unconfirmed'
                else:
                    return 'notified'
        if not self.time_received:
            if self.time_created + PAYMENT_TIMEOUT < timezone.now():
                return 'timeout'
            else:
                if 0 < self.paid_btc_amount < self.btc_amount:
                    return 'underpaid'
                else:
                    return 'new'
        else:
            if self.time_created + PAYMENT_VALIDATION_TIMEOUT < timezone.now():
                return 'failed'
            elif (
                not self.instantfiat_invoice_id and self.time_forwarded or
                self.instantfiat_invoice_id and self.time_exchanged
            ):
                return 'processed'
            elif self.time_forwarded:
                return 'forwarded'
            else:
                return 'received'

    @property
    def receipt_url(self):
        return construct_absolute_url(
            'api:short:payment-receipt',
            kwargs={'uid': self.uid})

    @property
    def btc_amount(self):
        """
        Total BTC amount (for receipts)
        """
        return (self.merchant_btc_amount +
                self.instantfiat_btc_amount +
                self.fee_btc_amount +
                self.tx_fee_btc_amount)

    @property
    def effective_exchange_rate(self):
        return (self.fiat_amount / self.btc_amount).quantize(BTC_DEC_PLACES)

    def create_payment_request(self, response_url):
        return create_payment_request(
            self.bitcoin_network,
            [(self.local_address, self.btc_amount)],
            self.time_created,
            self.expires_at,
            response_url,
            self.merchant.company_name)


def gen_withdrawal_uid():
    bts = uuid.uuid4().bytes
    return base58.encode(bts)[:6]


class WithdrawalOrder(models.Model):

    order_type = 'withdrawal'

    uid = models.CharField('UID',
                           max_length=32,
                           editable=False,
                           unique=True,
                           default=gen_withdrawal_uid)
    device = models.ForeignKey(
        'website.Device',
        on_delete=models.SET_NULL,
        null=True)
    # TODO: this field should be mandatory
    account = models.ForeignKey('website.Account', null=True)

    bitcoin_network = models.CharField(
        max_length=10, choices=BITCOIN_NETWORKS)
    merchant_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address], null=True)
    customer_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address], null=True)
    fiat_currency = models.ForeignKey('website.Currency')
    fiat_amount = models.DecimalField(
        max_digits=12, decimal_places=2)
    customer_btc_amount = models.DecimalField(
        max_digits=18, decimal_places=8)
    tx_fee_btc_amount = models.DecimalField(
        max_digits=18, decimal_places=8)
    change_btc_amount = models.DecimalField(
        max_digits=18, decimal_places=8)
    # TODO: remove this field
    exchange_rate = models.DecimalField(
        max_digits=18, decimal_places=8)

    reserved_outputs = models.BinaryField(editable=False)
    outgoing_tx_id = models.CharField(
        max_length=64,
        validators=[validate_transaction],
        null=True)
    instantfiat_transfer_id = models.CharField(
        max_length=50,
        null=True)
    instantfiat_reference = models.CharField(
        max_length=50,
        null=True)

    time_created = models.DateTimeField(auto_now_add=True)
    time_sent = models.DateTimeField(null=True)
    time_broadcasted = models.DateTimeField(null=True)
    time_notified = models.DateTimeField(null=True)
    time_confirmed = models.DateTimeField(null=True)
    time_cancelled = models.DateTimeField(null=True)

    def __unicode__(self):
        return self.uid

    @property
    def merchant(self):
        if self.account:
            return self.account.merchant
        else:
            return self.device.merchant

    @property
    def btc_amount(self):
        """
        Total BTC amount (for receipts)
        """
        return self.customer_btc_amount + self.tx_fee_btc_amount

    @property
    def effective_exchange_rate(self):
        return (self.fiat_amount / self.btc_amount).quantize(BTC_DEC_PLACES)

    @property
    def receipt_url(self):
        return construct_absolute_url(
            'api:short:withdrawal-receipt',
            kwargs={'uid': self.uid})

    @property
    def expires_at(self):
        return self.time_created + WITHDRAWAL_TIMEOUT

    @property
    def status(self):
        """
        Returns status of the withdrawal:
            new - withdrawal order has just been created
            sent - transaction has been sent
            broadcasted: transaction has been broadcasted
            completed (notified): customer notified about successful withdrawal
            confirmed - outgoing transaction confirmed
            timeout - transaction has not been sent
                (order is not confirmed)
            failed - transaction has been sent,
                but withdrawal order is not marked as notified
            unconfirmed - customer notified about successful withdrawal,
                but outgoing transaction is not confirmed
            cancelled: withdrawal order cancelled by the customer
        """
        if self.time_notified:
            if self.time_confirmed:
                return 'confirmed'
            else:
                if self.time_created + WITHDRAWAL_CONFIRMATION_TIMEOUT < timezone.now():
                    return 'unconfirmed'
                else:
                    return 'completed'
        if self.time_cancelled:
            return 'cancelled'
        if self.time_sent:
            if self.time_created + WITHDRAWAL_BROADCAST_TIMEOUT < timezone.now():
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


# TODO: remove this function
def gen_payment_reference():
    bts = uuid.uuid4().bytes
    return base58.encode(bts)[:10].upper()

import datetime
from decimal import Decimal
import uuid

from bitcoin import base58

from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django_countries.fields import CountryField
from django.contrib.sites.models import Site
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from website.models import BITCOIN_NETWORKS
from website.validators import (
    validate_post_code,
    validate_bitcoin_address,
    validate_transaction)

from operations import BTC_DEC_PLACES, blockr


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
    device = models.ForeignKey('website.Device')
    request = models.BinaryField(editable=False)

    # Payment details
    bitcoin_network = models.CharField(
        max_length=10, choices=BITCOIN_NETWORKS)
    local_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address])
    merchant_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address])
    fee_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address])
    instantfiat_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address], null=True)
    refund_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address], null=True)
    fiat_currency = models.ForeignKey('website.Currency')
    fiat_amount = models.DecimalField(
        max_digits=20, decimal_places=8)
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
    extra_btc_amount = models.DecimalField(
        max_digits=18, decimal_places=8, default=0)
    btc_amount = models.DecimalField(
        max_digits=20, decimal_places=8)
    instantfiat_invoice_id = models.CharField(
        max_length=255, null=True)

    incoming_tx_id = models.CharField(
        max_length=64, validators=[validate_transaction], null=True)
    outgoing_tx_id = models.CharField(
        max_length=64, validators=[validate_transaction], null=True)
    payment_type = models.CharField(
        max_length=10, choices=PAYMENT_TYPES)

    time_created = models.DateTimeField(auto_now_add=True)
    time_recieved = models.DateTimeField(null=True)
    time_forwarded = models.DateTimeField(null=True)
    time_broadcasted = models.DateTimeField(null=True)
    time_exchanged = models.DateTimeField(null=True)
    time_finished = models.DateTimeField(null=True)

    receipt_key = models.CharField(max_length=32, unique=True, null=True)

    def __unicode__(self):
        return str(self.pk)

    @property
    def status(self):
        """
        Returns status of the payment:
            new - payment order has just been created
            recieved - incoming transaction receieved
            forwarded - payment forwarded
            processed - recieved confirmation from instantfiat service
            completed - customer notified about successful payment
            timeout - incoming transaction did not recieved
            failed - incoming transaction recieved,
                but payment order is not marked as finished
        """
        if self.time_finished:
            return 'completed'
        if not self.time_recieved:
            if self.expires < timezone.now():
                return 'timeout'
            else:
                return 'new'
        else:
            if self.expires < timezone.now():
                return 'failed'
            elif (
                not self.instantfiat_invoice_id and self.time_forwarded
                or self.instantfiat_invoice_id and self.time_exchanged
            ):
                return 'processed'
            elif self.time_forwarded:
                return 'forwarded'
            else:
                return 'recieved'

    @property
    def expires(self):
        return self.time_created + datetime.timedelta(minutes=10)

    def is_receipt_ready(self):
        """
        Equivalent to:
            status in ['forwarded', 'processed', 'completed']
        """
        return self.time_forwarded is not None

    @property
    def receipt_url(self):
        domain = Site.objects.get_current().domain
        path = reverse('api:short:receipt', kwargs={'order_uid': self.uid})
        return 'https://{0}{1}'.format(domain, path)

    @property
    def incoming_tx_url(self):
        """For receipts"""
        return blockr.get_tx_url(self.incoming_tx_id, self.device.bitcoin_network)

    @property
    def payment_address_url(self):
        """For receipts"""
        return blockr.get_address_url(self.local_address, self.device.bitcoin_network)

    @property
    def effective_exchange_rate(self):
        return (self.fiat_amount / self.btc_amount).quantize(BTC_DEC_PLACES)

    @property
    def scaled_btc_amount(self):
        return self.btc_amount * settings.BITCOIN_SCALE_DIVIZER

    @property
    def scaled_effective_exchange_rate(self):
        return self.effective_exchange_rate / settings.BITCOIN_SCALE_DIVIZER


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
    device = models.ForeignKey('website.Device')

    bitcoin_network = models.CharField(
        max_length=10, choices=BITCOIN_NETWORKS)
    merchant_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address])
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
    exchange_rate = models.DecimalField(
        max_digits=18, decimal_places=8)

    reserved_outputs = models.BinaryField(editable=False)
    outgoing_tx_id = models.CharField(
        max_length=64,
        validators=[validate_transaction],
        null=True)

    time_created = models.DateTimeField(auto_now_add=True)
    time_sent = models.DateTimeField(null=True)
    time_broadcasted = models.DateTimeField(null=True)
    time_completed = models.DateTimeField(null=True)

    def __unicode__(self):
        return self.uid

    @property
    def btc_amount(self):
        """
        Total BTC amount
        """
        return self.customer_btc_amount + self.tx_fee_btc_amount

    @property
    def effective_exchange_rate(self):
        return (self.fiat_amount / self.btc_amount).quantize(BTC_DEC_PLACES)

    @property
    def scaled_btc_amount(self):
        return self.btc_amount * settings.BITCOIN_SCALE_DIVIZER

    @property
    def scaled_effective_exchange_rate(self):
        return self.effective_exchange_rate / settings.BITCOIN_SCALE_DIVIZER

    @property
    def outgoing_tx_url(self):
        """For receipts"""
        return blockr.get_tx_url(self.outgoing_tx_id, self.bitcoin_network)

    @property
    def customer_address_url(self):
        """For receipts"""
        return blockr.get_address_url(self.customer_address, self.bitcoin_network)

    @property
    def receipt_url(self):
        domain = Site.objects.get_current().domain
        path = reverse('api:short:receipt', kwargs={'order_uid': self.uid})
        return 'https://{0}{1}'.format(domain, path)

    @property
    def expires_at(self):
        return self.time_created + datetime.timedelta(minutes=10)

    @property
    def status(self):
        """
        Returns status of the withdrawal:
            new - withdrawal order has just been created
            sent - transaction has been sent
            broadcasted: transaction has been broadcasted
            completed: cutomer notified about successful withdrawal
            timeout - transaction has not been sent
            failed - transaction has been sent,
                but withdrawal order is not marked as completed
        """
        if self.time_completed:
            return 'completed'
        if self.time_sent:
            if self.expires_at >= timezone.now():
                if self.time_broadcasted:
                    return 'broadcasted'
                else:
                    return 'sent'
            else:
                return 'failed'
        else:
            if self.expires_at >= timezone.now():
                return 'new'
            else:
                return 'timeout'


def gen_payment_reference():
    bts = uuid.uuid4().bytes
    return base58.encode(bts)[:10].upper()


class Order(models.Model):

    PAYMENT_METHODS = [
        ('bitcoin', _('Bitcoin')),
        ('wire', _('Bank wire transfer')),
    ]
    PAYMENT_STATUSES = [
        ('unpaid', 'unpaid'),
        ('paid', 'paid'),
    ]

    merchant = models.ForeignKey('website.MerchantAccount')
    created = models.DateTimeField(auto_now_add=True)
    quantity = models.IntegerField()
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default='bitcoin')
    fiat_total_amount = models.DecimalField(max_digits=20, decimal_places=8)

    delivery_address = models.CharField(max_length=255, blank=True)
    delivery_address1 = models.CharField('', max_length=255, blank=True)
    delivery_address2 = models.CharField('', max_length=255, blank=True)
    delivery_town = models.CharField(max_length=64, blank=True)
    delivery_county = models.CharField(max_length=128, blank=True)
    delivery_post_code = models.CharField(max_length=32, blank=True, validators=[validate_post_code])
    delivery_country = CountryField(default='GB', blank=True)
    delivery_contact_phone = models.CharField(max_length=32, blank=True)

    instantfiat_invoice_id = models.CharField(max_length=255, null=True)
    instantfiat_btc_total_amount = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    instantfiat_address = models.CharField(max_length=35, validators=[validate_bitcoin_address], null=True)

    payment_reference = models.CharField(max_length=10, unique=True, editable=False, default=gen_payment_reference)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUSES, default='unpaid')

    def __unicode__(self):
        return "order #{0}".format(self.id)

    @property
    def fiat_amount(self):
        return self.fiat_total_amount / Decimal(1.2)

    @property
    def fiat_vat_amount(self):
        return self.fiat_amount * Decimal(0.2)

    @property
    def instantfiat_btc_amount(self):
        return self.instantfiat_btc_total_amount / Decimal(1.2)

    @property
    def instantfiat_btc_vat_amount(self):
        return self.instantfiat_btc_amount * Decimal(0.2)

    @property
    def invoice_due_date(self):
        return self.created + datetime.timedelta(days=14)
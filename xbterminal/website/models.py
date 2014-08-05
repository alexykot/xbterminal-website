# -*- coding: utf-8 -*-
import uuid
import datetime
from decimal import Decimal

from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django_countries.fields import CountryField
from django.contrib.sites.models import Site
from django.utils import timezone

from website.validators import validate_percent, validate_bitcoin, validate_transaction
from website.fields import FirmwarePathField


class Language(models.Model):
    name = models.CharField(max_length=50)
    fractional_split = models.CharField(max_length=1, default=".")
    thousands_split = models.CharField(max_length=1, default=",")

    def __unicode__(self):
        return self.name


class Currency(models.Model):
    name = models.CharField(max_length=50)
    postfix = models.CharField(max_length=50, default="")
    prefix = models.CharField(max_length=50, default="")

    class Meta:
        verbose_name_plural = 'currencies'

    def __unicode__(self):
        return self.name


class MerchantAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="merchant", null=True)
    company_name = models.CharField(max_length=254)
    trading_name = models.CharField(max_length=254, blank=True)
    business_address = models.CharField(max_length=1000)
    business_address1 = models.CharField('', max_length=1000, blank=True, default='')
    business_address2 = models.CharField('', max_length=1000, blank=True, default='')
    town = models.CharField(max_length=1000)
    county = models.CharField("State / County", max_length=100, blank=True)
    post_code = models.CharField(max_length=1000)
    country = CountryField(default='GB')
    contact_first_name = models.CharField(max_length=1000)
    contact_last_name = models.CharField(max_length=1000)
    contact_phone = models.CharField(max_length=1000)
    contact_email = models.EmailField(unique=True)

    language = models.ForeignKey(Language, default=1)  # by default, English, see fixtures
    currency = models.ForeignKey(Currency, default=1)  # by default, GBP, see fixtures

    def __unicode__(self):
        return self.company_name

    def get_address(self):
        strings = [self.business_address, self.business_address1, self.business_address2,
                   self.town, self.county, unicode(self.country.name)]
        return ', '.join(filter(None, strings))


class Device(models.Model):

    DEVICE_TYPES = [
        ('mobile', 'Mobile app'),
        ('hardware', 'Terminal'),
        ('web', 'Web app'),
    ]
    PAYMENT_PROCESSING_CHOICES = [
        ('keep', 'keep bitcoins'),
        ('partially', 'convert partially'),
        ('full', 'convert full amount'),
    ]
    PAYMENT_PROCESSOR_CHOICES = [
        ('BitPay', 'BitPay'),
        ('CryptoPay', 'CryptoPay'),
        ('GoCoin', 'GoCoin'),
    ]

    merchant = models.ForeignKey(MerchantAccount)
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPES)
    name = models.CharField('Your reference', max_length=100)

    payment_processing = models.CharField(max_length=50, choices=PAYMENT_PROCESSING_CHOICES, default='keep')
    payment_processor = models.CharField(max_length=50, choices=PAYMENT_PROCESSOR_CHOICES, null=True)
    api_key = models.CharField(max_length=100)
    percent = models.DecimalField(
        'percent to convert',
        max_digits=4,
        decimal_places=1,
        blank=True,
        validators=[validate_percent],
        null=True
    )
    bitcoin_address = models.CharField('bitcoin address to send to', max_length=100, blank=True)

    key = models.CharField(max_length=32, editable=False, unique=True, default=lambda: uuid.uuid4().hex)

    serial_number = models.CharField(max_length=50, blank=True, null=True)
    bitcoin_network = models.CharField(max_length=50, blank=True, null=True)

    last_activity = models.DateTimeField(null=True)
    last_reconciliation = models.DateTimeField(auto_now_add=True)

    # firmware data
    current_firmware = models.ForeignKey("Firmware", related_name='current_for_device_set', blank=True, null=True)
    last_firmware_update_date = models.DateTimeField(blank=True, null=True)
    next_firmware = models.ForeignKey("Firmware", related_name='next_to_device_set', blank=True, null=True)

    our_fee_override = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ['id']

    def __unicode__(self):
        return 'device: %s' % self.name

    def save(self, *args, **kwargs):
        super(Device, self).save(*args, **kwargs)

    def payment_processor_info(self):
        if self.payment_processing in ['partially', 'full']:
            return '%s, %s%% converted' % (self.payment_processor, self.percent)
        return ''

    def get_transactions_by_date(self, date):
        return self.transaction_set.filter(
            time__range=(datetime.datetime.combine(date, datetime.time.min),
                         datetime.datetime.combine(date, datetime.time.max))
        )

    def is_online(self):
        if self.last_activity is None:
            return False
        delta = timezone.now() - self.last_activity
        return delta < datetime.timedelta(minutes=2)


class ReconciliationTime(models.Model):
    device = models.ForeignKey(Device, related_name="rectime_set")
    email = models.EmailField()
    time = models.TimeField()

    class Meta:
        ordering = ['time']


class Transaction(models.Model):
    device = models.ForeignKey(Device)
    hop_address = models.CharField(max_length=35, validators=[validate_bitcoin])
    dest_address = models.CharField(max_length=35, validators=[validate_bitcoin], blank=True, null=True)
    instantfiat_address = models.CharField(max_length=35, validators=[validate_bitcoin], blank=True, null=True)
    bitcoin_transaction_id_1 = models.CharField(max_length=64, validators=[validate_transaction])
    bitcoin_transaction_id_2 = models.CharField(max_length=64, validators=[validate_transaction])
    fiat_currency = models.CharField(max_length=3)
    fiat_amount = models.DecimalField(max_digits=20, decimal_places=8)
    btc_amount = models.DecimalField(max_digits=20, decimal_places=8)
    effective_exchange_rate = models.DecimalField(max_digits=20, decimal_places=8)
    instantfiat_fiat_amount = models.DecimalField(max_digits=9, decimal_places=2, blank=True, default=0)
    instantfiat_btc_amount = models.DecimalField(max_digits=18, decimal_places=8, blank=True, default=0)
    fee_btc_amount = models.DecimalField(max_digits=18, decimal_places=8, blank=True, default=0)
    instantfiat_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    time = models.DateTimeField()

    date_created = models.DateTimeField(auto_now_add=True)
    receipt_key = models.CharField(max_length=32, editable=False, unique=True, default=lambda: uuid.uuid4().hex)

    def get_api_url(self):
        domain = Site.objects.get_current().domain
        path = reverse('api:transaction_pdf', kwargs={'key': self.receipt_key})
        return 'https://%s%s' % (domain, path)

    def get_blockchain_transaction_url(self):
        return 'https://blockchain.info/en/tx/%s' % self.bitcoin_transaction_id_1

    def get_blockchain_address_url(self, address):
        return 'https://blockchain.info/en/address/%s' % address

    def get_dest_address_url(self):
        return self.get_blockchain_address_url(self.dest_address)

    def scaled_total_btc_amount(self):
        return self.btc_amount * settings.BITCOIN_SCALE_DIVIZER

    def scaled_effective_exchange_rate(self):
        return self.effective_exchange_rate / settings.BITCOIN_SCALE_DIVIZER

    def scaled_btc_amount(self):
        return self.scaled_total_btc_amount() - self.fee_btc_amount

    def scaled_exchange_rate(self):
        return self.fiat_amount / self.scaled_btc_amount()


class Firmware(models.Model):
    hash = models.CharField(max_length=32, editable=False, unique=True, default=lambda: uuid.uuid4().hex)
    version = models.CharField(max_length=50)
    comment = models.TextField(blank=True)
    added = models.DateField(auto_now_add=True)
    filename = FirmwarePathField(path=settings.FIRMWARE_PATH)

    def __unicode__(self):
        return 'firmware %s' % self.version


class PaymentOrder(models.Model):

    uid = models.CharField(max_length=32,
                           editable=False,
                           unique=True,
                           default=lambda: uuid.uuid4().hex)
    device = models.ForeignKey(Device)
    request = models.BinaryField()
    created = models.DateTimeField()
    expires = models.DateTimeField()
    

    # Payment details
    local_address = models.CharField(max_length=35, validators=[validate_bitcoin])
    merchant_address = models.CharField(max_length=35, validators=[validate_bitcoin])
    fee_address = models.CharField(max_length=35, validators=[validate_bitcoin])
    instantfiat_address = models.CharField(max_length=35, validators=[validate_bitcoin], null=True)
    fiat_currency = models.CharField(max_length=3)
    fiat_amount = models.DecimalField(max_digits=20, decimal_places=8)
    instantfiat_fiat_amount = models.DecimalField(max_digits=9, decimal_places=2)
    instantfiat_btc_amount = models.DecimalField(max_digits=18, decimal_places=8)
    merchant_btc_amount = models.DecimalField(max_digits=18, decimal_places=8)
    fee_btc_amount = models.DecimalField(max_digits=18, decimal_places=8)
    extra_btc_amount = models.DecimalField(max_digits=18, decimal_places=8, default=0)
    btc_amount = models.DecimalField(max_digits=20, decimal_places=8)
    effective_exchange_rate = models.DecimalField(max_digits=20, decimal_places=8)
    instantfiat_invoice_id = models.CharField(max_length=255, null=True)

    incoming_tx_id = models.CharField(max_length=64, validators=[validate_transaction], null=True)
    outgoing_tx_id = models.CharField(max_length=64, validators=[validate_transaction], null=True)
    transaction = models.OneToOneField(Transaction, null=True)


class Order(models.Model):

    PAYMENT_METHODS = [
        ('bitcoin', 'Bitcoin'),
        ('wire', 'Wire transfer'),
    ]

    merchant = models.ForeignKey(MerchantAccount)
    created = models.DateTimeField(auto_now_add=True)
    quantity = models.IntegerField()
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, default='bitcoin')
    fiat_total_amount = models.DecimalField(max_digits=20, decimal_places=8)

    delivery_address = models.CharField(max_length=1000, blank=True)
    delivery_address1 = models.CharField('', max_length=1000, blank=True)
    delivery_address2 = models.CharField('', max_length=1000, blank=True)
    delivery_town = models.CharField(max_length=1000, blank=True)
    delivery_county = models.CharField("Delivery state / county", max_length=100, blank=True)
    delivery_post_code = models.CharField(max_length=1000, blank=True)
    delivery_country = CountryField(default='GB', blank=True)
    delivery_contact_phone = models.CharField(max_length=1000, blank=True)

    instantfiat_invoice_id = models.CharField(max_length=255, null=True)
    instantfiat_btc_total_amount = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    instantfiat_address = models.CharField(max_length=35, validators=[validate_bitcoin], null=True)

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

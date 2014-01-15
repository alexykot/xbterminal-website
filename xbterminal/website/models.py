# -*- coding: utf-8 -*-
import uuid

from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django_countries.fields import CountryField
from django.contrib.sites.models import Site

from website.validators import validate_percent, validate_bitcoin, validate_transaction


class MerchantAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="merchant", null=True)
    company_name = models.CharField(max_length=254)
    business_address = models.CharField(max_length=1000)
    business_address1 = models.CharField('', max_length=1000, blank=True, default='')
    business_address2 = models.CharField('', max_length=1000, blank=True, default='')
    town = models.CharField(max_length=1000)
    country = CountryField(default='GB')
    county = models.CharField("State / County", max_length=100, blank=True)
    post_code = models.CharField(max_length=1000)
    contact_name = models.CharField(max_length=1000)
    contact_phone = models.CharField(max_length=1000)
    contact_email = models.EmailField(unique=True)

    def __unicode__(self):
        return self.company_name

    def get_first_device_url(self):
        if not self.device_set.exists():
            return reverse('website:create_device')
        return reverse('website:device', kwargs={'number': 1})

    def get_address(self):
        strings = [self.business_address, self.business_address1, self.business_address2,
                   self.town, self.county, unicode(self.country.name)]
        return ', '.join(filter(None, strings))


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


class Device(models.Model):
    PAYMENT_PROCESSING_CHOICES = (
        ('keep', 'keep bitcoins'),
        ('partially', 'convert partially'),
        ('full', 'convert full amount')
    )
    PAYMENT_PROCESSOR_CHOICES = (
        ('BitPay', 'BitPay'),
        ('BIPS', 'BIPS'),
        ('CryptoPay', 'CryptoPay')
    )
    merchant = models.ForeignKey(MerchantAccount)

    name = models.CharField(max_length=100)
    language = models.ForeignKey(Language, default=1)  # by default, English, see fixtures
    currency = models.ForeignKey(Currency, default=1)  # by default, GBP, see fixtures
    comment = models.CharField(max_length=100, blank=True)
    payment_processing = models.CharField(max_length=50, choices=PAYMENT_PROCESSING_CHOICES, default='keep')
    payment_processor = models.CharField(max_length=50, choices=PAYMENT_PROCESSOR_CHOICES, null=True)
    api_key = models.CharField(max_length=100, blank=True)
    percent = models.DecimalField(
        'percent to convert',
        max_digits=4,
        decimal_places=1,
        blank=True,
        validators=[validate_percent],
        null=True
    )
    bitcoin_address = models.CharField('bitcoin address to send to', max_length=100, blank=True)

    key = models.CharField(max_length=32, editable=False, unique=True, default=lambda:uuid.uuid4().hex)

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


class Transaction(models.Model):
    device = models.ForeignKey(Device)
    source_address = models.CharField(max_length=35, validators=[validate_bitcoin])
    hop_address = models.CharField(max_length=35, validators=[validate_bitcoin])
    dest_address = models.CharField(max_length=35, validators=[validate_bitcoin])
    bitcoin_transaction_id_1 = models.CharField(max_length=64, validators=[validate_transaction])
    bitcoin_transaction_id_2 = models.CharField(max_length=64, validators=[validate_transaction])
    fiat_amount = models.DecimalField(max_digits=20, decimal_places=8)
    btc_amount = models.DecimalField(max_digits=20, decimal_places=8)
    effective_exchange_rate = models.DecimalField(max_digits=20, decimal_places=8)
    time = models.DateTimeField()

    key = models.CharField(max_length=32, editable=False, unique=True, default=lambda:uuid.uuid4().hex)

    def get_api_url(self):
        domain = Site.objects.get_current().domain
        path = reverse('api:transaction_pdf', kwargs={'key': self.key})
        return 'https://%s%s' % (domain, path)

    def get_blockchain_transaction_url(self):
        return 'https://blockchain.info/en/tx/%s' % self.bitcoin_transaction_id_1

    def get_blockchain_address_url(self, address):
        return 'https://blockchain.info/en/address/%s' % address

    def get_source_address_url(self):
        return self.get_blockchain_address_url(self.source_address)

    def get_dest_address_url(self):
        return self.get_blockchain_address_url(self.dest_address)

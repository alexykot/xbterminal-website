import datetime
from decimal import Decimal
import uuid

from bitcoin import base58

from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django_countries.fields import CountryField
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.sites.models import Site
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from constance import config

from website.validators import (
    validate_phone,
    validate_post_code,
    validate_percent,
    validate_bitcoin_address,
    validate_transaction)
from website.fields import FirmwarePathField


class UserManager(BaseUserManager):

    def _create_user(self, email, password, is_staff, is_superuser):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        user = self.model(email=self.normalize_email(email),
                          is_staff=is_staff,
                          is_superuser=is_superuser)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None):
        return self._create_user(email, password, False, False)

    def create_superuser(self, email, password):
        return self._create_user(email, password, True, True)


class User(AbstractBaseUser, PermissionsMixin):

    email = models.EmailField(max_length=254, unique=True)

    is_staff = models.BooleanField(
        'staff status',
        default=False,
        help_text='Designates whether the user can log into this admin site.')
    is_active = models.BooleanField(
        'active',
        default=True,
        help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.')

    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def get_full_name(self):
        return self.email

    def get_short_name(self):
        return self.email


class Language(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=2)
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
    company_name = models.CharField(_('Company name'), max_length=255)
    trading_name = models.CharField(_('Trading name'), max_length=255, blank=True)
    business_address = models.CharField(_('Business address'), max_length=255)
    business_address1 = models.CharField('', max_length=255, blank=True, default='')
    business_address2 = models.CharField('', max_length=255, blank=True, default='')
    town = models.CharField(_('Town'), max_length=64)
    county = models.CharField(_('State / County'), max_length=128, blank=True)
    post_code = models.CharField(_('Post code'), max_length=32, validators=[validate_post_code])
    country = CountryField(_('Country'), default='GB')
    contact_first_name = models.CharField(_('Contact first name'), max_length=255)
    contact_last_name = models.CharField(_('Contact last name'), max_length=255)
    contact_phone = models.CharField(_('Contact phone'), max_length=32, validators=[validate_phone])
    contact_email = models.EmailField(_('Contact email'), max_length=254, unique=True)

    language = models.ForeignKey(Language, default=1)  # by default, English, see fixtures
    currency = models.ForeignKey(Currency, default=1)  # by default, GBP, see fixtures

    def __unicode__(self):
        return self.company_name

    @property
    def billing_address(self):
        strings = [
            self.business_address,
            self.business_address1,
            self.town,
            self.county,
            self.post_code,
            self.country.name,
        ]
        return [s for s in strings if s]

    @property
    def info(self):
        active_dt = timezone.now() - datetime.timedelta(minutes=2)
        active = self.device_set.filter(last_activity__gte=active_dt).count()
        total =  self.device_set.count()
        today = timezone.localtime(timezone.now()).\
            replace(hour=0, minute=0, second=0, microsecond=0)
        transactions = Transaction.objects.filter(device__merchant=self,
                                                  time__gte=today)
        tx_count = transactions.count()
        tx_sum = transactions.aggregate(s=models.Sum('fiat_amount'))['s']
        return {'name': self.trading_name or self.company_name,
                'active': active,
                'total': total,
                'tx_count': tx_count,
                'tx_sum': 0 if tx_sum is None else tx_sum}


def gen_device_key():
    bts = uuid.uuid4().bytes
    return base58.encode(bts)[:8]


class Device(models.Model):

    DEVICE_TYPES = [
        ('hardware', _('Terminal')),
        ('mobile', _('Mobile app')),
        ('web', _('Web app')),
    ]
    DEVICE_STATUSES = [
        ('preordered', _('Preordered')),
        ('dispatched', _('Dispatched')),
        ('delivered', _('Delivered')),
        ('active', _('Online')),
        ('suspended', _('Suspended')),
        ('disposed', _('Disposed')),
    ]
    PAYMENT_PROCESSING_CHOICES = [
        ('keep', _('keep bitcoins')),
        ('partially', _('convert partially')),
        ('full', _('convert full amount')),
    ]
    PAYMENT_PROCESSOR_CHOICES = [
        ('BitPay', 'BitPay'),
        ('CryptoPay', 'CryptoPay'),
        ('GoCoin', 'GoCoin'),
    ]
    BITCOIN_NETWORKS = [
        ('mainnet', 'Main'),
        ('testnet', 'Testnet'),
    ]

    merchant = models.ForeignKey(MerchantAccount)
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPES)
    status = models.CharField(max_length=50, choices=DEVICE_STATUSES, default='active')
    name = models.CharField(_('Your reference'), max_length=100)

    payment_processing = models.CharField(_('Payment processing'), max_length=50, choices=PAYMENT_PROCESSING_CHOICES, default='keep')
    payment_processor = models.CharField(_('Payment processor'), max_length=50, choices=PAYMENT_PROCESSOR_CHOICES, default='GoCoin')
    api_key = models.CharField(_('API key'), max_length=255, blank=True)
    percent = models.DecimalField(
        _('Percent to convert'),
        max_digits=4,
        decimal_places=1,
        validators=[validate_percent],
        default=0)
    bitcoin_address = models.CharField(_('Bitcoin address to send to'), max_length=100, blank=True)

    key = models.CharField(_('Device key'), max_length=32, editable=False, unique=True, default=gen_device_key)

    serial_number = models.CharField(max_length=50, blank=True, null=True)
    bitcoin_network = models.CharField(max_length=50, choices=BITCOIN_NETWORKS, default='mainnet')

    last_activity = models.DateTimeField(blank=True, null=True)
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

    @property
    def our_fee_address(self):
        if self.our_fee_override:
            return self.our_fee_override
        if self.bitcoin_network == 'mainnet':
            return config.OUR_FEE_MAINNET_ADDRESS
        elif self.bitcoin_network == 'testnet':
            return config.OUR_FEE_TESTNET_ADDRESS


class ReconciliationTime(models.Model):
    device = models.ForeignKey(Device, related_name="rectime_set")
    email = models.EmailField(max_length=254)
    time = models.TimeField()

    class Meta:
        ordering = ['time']


class Transaction(models.Model):
    device = models.ForeignKey(Device)
    hop_address = models.CharField(max_length=35, validators=[validate_bitcoin_address])
    dest_address = models.CharField(max_length=35, validators=[validate_bitcoin_address], blank=True, null=True)
    instantfiat_address = models.CharField(max_length=35, validators=[validate_bitcoin_address], blank=True, null=True)
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
    local_address = models.CharField(max_length=35, validators=[validate_bitcoin_address])
    merchant_address = models.CharField(max_length=35, validators=[validate_bitcoin_address])
    fee_address = models.CharField(max_length=35, validators=[validate_bitcoin_address])
    instantfiat_address = models.CharField(max_length=35, validators=[validate_bitcoin_address], null=True)
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

    def __unicode__(self):
        return "Payment order {0}".format(self.uid)


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

    merchant = models.ForeignKey(MerchantAccount)
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

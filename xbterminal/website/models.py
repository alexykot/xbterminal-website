import datetime
from decimal import Decimal
import os
import uuid

from bitcoin import base58

from django.db import models
from django.conf import settings
from django.core.files.storage import FileSystemStorage
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
from website.files import get_verification_file_name, verification_file_path_gen

from payment import BTC_DEC_PLACES, blockr


class UserManager(BaseUserManager):

    def _create_user(self, email, password, is_staff, is_superuser, commit):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        user = self.model(email=self.normalize_email(email),
                          is_staff=is_staff,
                          is_superuser=is_superuser)
        user.set_password(password)
        if commit:
            user.save(using=self._db)
        return user

    def create_user(self, email, password=None, commit=True):
        return self._create_user(email, password, False, False, commit)

    def create_superuser(self, email, password):
        return self._create_user(email, password, True, True, True)


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
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=2, unique=True)
    fractional_split = models.CharField(max_length=1, default=".")
    thousands_split = models.CharField(max_length=1, default=",")

    def __unicode__(self):
        return self.name


def get_language(country_code):
    if country_code == 'FR':
        language_code = 'fr'
    elif country_code in ['DE', 'AT', 'CH']:
        language_code = 'de'
    elif country_code in ['RU', 'UA', 'BY', 'KZ']:
        language_code = 'ru'
    else:
        language_code = 'en'
    return Language.objects.get(code=language_code)


class Currency(models.Model):
    name = models.CharField(max_length=50, unique=True)
    postfix = models.CharField(max_length=50, default="")
    prefix = models.CharField(max_length=50, default="")

    class Meta:
        verbose_name_plural = 'currencies'

    def __unicode__(self):
        return self.name


def get_currency(country_code):
    if country_code == 'GB':
        currency_code = 'GBP'
    elif country_code in ['AT', 'BE', 'DE', 'GR', 'IE', 'ES',
                          'IT', 'CY', 'LV', 'LU', 'MT', 'NL',
                          'PT', 'SK', 'SI', 'FI', 'FR', 'EE']:
        # Eurozone
        currency_code = 'EUR'
    else:
        currency_code = 'USD'
    return Currency.objects.get(name=currency_code)


class MerchantAccount(models.Model):

    PAYMENT_PROCESSOR_CHOICES = [
        ('bitpay', 'BitPay'),
        ('cryptopay', 'CryptoPay'),
        ('gocoin', 'GoCoin'),
    ]

    VERIFICATION_STATUSES = [
        ('unverified', _('unverified')),
        ('pending', _('verification pending')),
        ('verified', _('verified')),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="merchant")
    company_name = models.CharField(_('Company name'), max_length=255, unique=True)
    trading_name = models.CharField(_('Trading name'), max_length=255, blank=True)

    business_address = models.CharField(_('Business address'), max_length=255, null=True)
    business_address1 = models.CharField('', max_length=255, blank=True, default='')
    business_address2 = models.CharField('', max_length=255, blank=True, default='')
    town = models.CharField(_('Town'), max_length=64, null=True)
    county = models.CharField(_('State / County'), max_length=128, blank=True, default='')
    post_code = models.CharField(_('Post code'), max_length=32, validators=[validate_post_code], null=True)
    country = CountryField(_('Country'), default='GB')

    contact_first_name = models.CharField(_('Contact first name'), max_length=255)
    contact_last_name = models.CharField(_('Contact last name'), max_length=255)
    contact_phone = models.CharField(_('Contact phone'), max_length=32, validators=[validate_phone], null=True)
    contact_email = models.EmailField(_('Contact email'), max_length=254, unique=True)

    language = models.ForeignKey(Language, default=1)  # by default, English, see fixtures
    currency = models.ForeignKey(Currency, default=1)  # by default, GBP, see fixtures

    payment_processor = models.CharField(_('Payment processor'), max_length=50, choices=PAYMENT_PROCESSOR_CHOICES, default='gocoin')
    api_key = models.CharField(_('API key'), max_length=255, blank=True)
    gocoin_merchant_id = models.CharField(max_length=36, blank=True, null=True)

    verification_status = models.CharField(_('KYC'), max_length=50, choices=VERIFICATION_STATUSES, default='unverified')

    comments = models.TextField(blank=True)

    def __unicode__(self):
        if self.trading_name:
            return u'{0} ({1})'.format(self.company_name, self.trading_name)
        else:
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
    def contact_name(self):
        return self.contact_first_name + ' ' + self.contact_last_name

    @property
    def is_profile_complete(self):
        return (bool(self.business_address) and
                bool(self.town) and
                bool(self.post_code) and
                bool(self.contact_phone))

    def get_kyc_document(self, document_type, status):
        try:
            return self.kycdocument_set.\
                filter(document_type=document_type, status=status).\
                latest('uploaded')
        except KYCDocument.DoesNotExist:
            return None

    def get_latest_kyc_document(self, document_type):
        """
        Search for latest uploaded document
        """
        return self.kycdocument_set.\
            filter(document_type=document_type).\
            exclude(status='uploaded').\
            latest('uploaded')

    def get_account_balance(self, network):
        account = self.btcaccount_set.\
            filter(network=network).first()
        if account:
            return account.balance

    @property
    def info(self):
        if self.verification_status == 'verified':
            status = None
        else:
            status = self.get_verification_status_display()
        active_dt = timezone.now() - datetime.timedelta(minutes=2)
        active = self.device_set.filter(last_activity__gte=active_dt).count()
        total = self.device_set.count()
        today = timezone.localtime(timezone.now()).\
            replace(hour=0, minute=0, second=0, microsecond=0)
        transactions = Transaction.objects.filter(device__merchant=self,
                                                  time__gte=today)
        tx_count = transactions.count()
        tx_sum = transactions.aggregate(s=models.Sum('fiat_amount'))['s']
        return {'name': self.trading_name or self.company_name,
                'status': status,
                'active': active,
                'total': total,
                'tx_count': tx_count,
                'tx_sum': 0 if tx_sum is None else tx_sum}


BITCOIN_NETWORKS = [
    ('mainnet', 'Main'),
    ('testnet', 'Testnet'),
]


class BTCAccount(models.Model):

    merchant = models.ForeignKey(MerchantAccount)
    network = models.CharField(max_length=50,
                               choices=BITCOIN_NETWORKS,
                               default='mainnet')
    balance = models.DecimalField(max_digits=20,
                                  decimal_places=8,
                                  default=0)
    balance_max = models.DecimalField(max_digits=20,
                                      decimal_places=8,
                                      default=0)
    address = models.CharField(max_length=35,
                               validators=[validate_bitcoin_address],
                               blank=True,
                               null=True)

    def __unicode__(self):
        return '{0} - {1} account'.format(
            str(self.merchant),
            'BTC' if self.network == 'mainnet' else 'TBTC')


verification_file_storage = FileSystemStorage(
    location=os.path.join(settings.MEDIA_ROOT, 'verification'),
    base_url='/verification/')


class KYCDocument(models.Model):

    IDENTITY_DOCUMENT = 1
    CORPORATE_DOCUMENT = 2

    DOCUMENT_TYPES = [
        (IDENTITY_DOCUMENT, 'IdentityDocument'),
        (CORPORATE_DOCUMENT, 'CorporateDocument'),
    ]

    VERIFICATION_STATUSES = [
        ('uploaded', _('Uploaded')),
        ('unverified', _('Unverified')),
        ('denied', _('Denied')),
        ('verified', _('Verified')),
    ]

    merchant = models.ForeignKey(MerchantAccount)
    document_type = models.IntegerField(choices=DOCUMENT_TYPES)
    file = models.FileField(
        storage=verification_file_storage,
        upload_to=verification_file_path_gen)
    uploaded = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=VERIFICATION_STATUSES, default='uploaded')
    gocoin_document_id = models.CharField(max_length=36, blank=True, null=True)
    comment = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = 'KYC document'

    def __unicode__(self):
        return "{0} - {1}".format(
            self.merchant.company_name,
            self.get_document_type_display())

    @property
    def base_name(self):
        return os.path.basename(self.file.name)

    @property
    def original_name(self):
        return get_verification_file_name(self.file)


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
        ('active', _('Operational')),
        ('suspended', _('Suspended')),
        ('disposed', _('Disposed')),
    ]
    PAYMENT_PROCESSING_CHOICES = [
        ('keep', _('keep bitcoins')),
        ('partially', _('convert partially')),
        ('full', _('convert full amount')),
    ]

    merchant = models.ForeignKey(MerchantAccount)
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPES)
    status = models.CharField(max_length=50, choices=DEVICE_STATUSES, default='active')
    name = models.CharField(_('Your reference'), max_length=100)

    percent = models.DecimalField(
        _('Percent to convert'),
        max_digits=4,
        decimal_places=1,
        validators=[validate_percent],
        default=100)
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
        return self.name

    @property
    def payment_processing(self):
        if self.percent == 0:
            return 'keep'
        elif self.percent == 100:
            return 'full'
        else:
            return 'partially'

    def payment_processor_info(self):
        if self.percent > 0:
            return '{0}, {1}% converted'.format(
                self.merchant.get_payment_processor_display(),
                self.percent)
        return ''

    def get_payments(self):
        return self.paymentorder_set.filter(time_finished__isnull=False)

    def get_payments_by_date(self, date):
        """
        Accepts:
            date_range: tuple or single date
        """
        if isinstance(date, datetime.date):
            beg = timezone.make_aware(
                datetime.datetime.combine(date, datetime.time.min),
                timezone.get_current_timezone())
            end = timezone.make_aware(
                datetime.datetime.combine(date, datetime.time.max),
                timezone.get_current_timezone())
        else:
            beg, end = date
        return self.paymentorder_set.filter(time_finished__range=(beg, end))

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

    def __unicode__(self):
        return str(self.pk)

    def get_api_url(self):
        domain = Site.objects.get_current().domain
        path = reverse('api:receipt', kwargs={'key': self.receipt_key})
        return 'https://%s%s' % (domain, path)

    def get_incoming_transaction_url(self):
        return blockr.get_tx_url(self.bitcoin_transaction_id_1, self.device.bitcoin_network)

    def get_hop_address_url(self):
        return blockr.get_address_url(self.hop_address, self.device.bitcoin_network)

    def scaled_total_btc_amount(self):
        return self.btc_amount * settings.BITCOIN_SCALE_DIVIZER

    def scaled_effective_exchange_rate(self):
        return self.effective_exchange_rate / settings.BITCOIN_SCALE_DIVIZER

    def scaled_btc_amount(self):
        return (self.btc_amount - self.fee_btc_amount) * settings.BITCOIN_SCALE_DIVIZER

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


def gen_payment_uid():
    bts = uuid.uuid4().bytes
    return base58.encode(bts)[:6]


class PaymentOrder(models.Model):

    PAYMENT_TYPES = [
        ('bip0021', _('BIP 0021 (Bitcoin URI)')),
        ('bip0070', _('BIP 0070 (Payment Protocol)')),
    ]

    uid = models.CharField('UID',
                           max_length=32,
                           editable=False,
                           unique=True,
                           default=gen_payment_uid)
    device = models.ForeignKey(Device)
    request = models.BinaryField(editable=False)

    # Payment details
    local_address = models.CharField(max_length=35, validators=[validate_bitcoin_address])
    merchant_address = models.CharField(max_length=35, validators=[validate_bitcoin_address])
    fee_address = models.CharField(max_length=35, validators=[validate_bitcoin_address])
    instantfiat_address = models.CharField(max_length=35, validators=[validate_bitcoin_address], null=True)
    refund_address = models.CharField(max_length=35, validators=[validate_bitcoin_address], null=True)
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
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPES)

    time_created = models.DateTimeField()
    time_recieved = models.DateTimeField(null=True)
    time_forwarded = models.DateTimeField(null=True)
    time_broadcasted = models.DateTimeField(null=True)
    time_exchanged = models.DateTimeField(null=True)
    time_finished = models.DateTimeField(null=True)

    transaction = models.OneToOneField(Transaction, null=True)
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
        path = reverse('api:short:receipt', kwargs={'payment_uid': self.uid})
        return 'https://{0}{1}'.format(domain, path)

    @property
    def incoming_tx_url(self):
        return blockr.get_tx_url(self.incoming_tx_id, self.device.bitcoin_network)

    @property
    def payment_address_url(self):
        return blockr.get_address_url(self.local_address, self.device.bitcoin_network)

    @property
    def scaled_btc_amount(self):
        return self.btc_amount * settings.BITCOIN_SCALE_DIVIZER

    @property
    def scaled_effective_exchange_rate(self):
        return self.effective_exchange_rate / settings.BITCOIN_SCALE_DIVIZER


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


def gen_withdrawal_uid():
    bts = uuid.uuid4().bytes
    return base58.encode(bts)[:6]


class WithdrawalOrder(models.Model):

    uid = models.CharField('UID',
                           max_length=32,
                           editable=False,
                           unique=True,
                           default=gen_withdrawal_uid)
    device = models.ForeignKey(Device)

    bitcoin_network = models.CharField(
        max_length=10, choices=BITCOIN_NETWORKS)
    merchant_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address])
    customer_address = models.CharField(
        max_length=35, validators=[validate_bitcoin_address], null=True)
    fiat_currency = models.ForeignKey(Currency)
    fiat_amount = models.DecimalField(
        max_digits=12, decimal_places=2)
    customer_btc_amount = models.DecimalField(
        max_digits=18, decimal_places=8)
    tx_fee_btc_amount = models.DecimalField(
        max_digits=18, decimal_places=8)
    exchange_rate = models.DecimalField(
        max_digits=18, decimal_places=8)

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

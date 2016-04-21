import datetime
import random
import os
import uuid

from bitcoin import base58

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin)
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from constance import config
from django_countries.fields import CountryField
from django_fsm import FSMField, transition

from website.validators import (
    validate_phone,
    validate_post_code,
    validate_percent,
    validate_bitcoin_address,
    validate_public_key)
from website.files import (
    get_verification_file_name,
    verification_file_path_gen,
    VerificationFileStorage)


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


class UITheme(models.Model):

    name = models.CharField(max_length=50, unique=True)

    def __unicode__(self):
        return self.name


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
    ui_theme = models.ForeignKey(UITheme, default=1)  # 'default' theme, see fixtures

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

    def get_account_balance(self, currency_name):
        account = self.account_set.\
            filter(currency__name=currency_name).first()
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
        transactions = apps.get_model('operations', 'PaymentOrder').\
            objects.filter(device__merchant=self, time_notified__gte=today)
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


class Account(models.Model):
    """
    Represents internal BTC account or external instantfiat account
    """
    merchant = models.ForeignKey(MerchantAccount)
    currency = models.ForeignKey(Currency)
    balance = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=0)
    balance_max = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=0)
    bitcoin_address = models.CharField(
        max_length=35,
        unique=True,
        validators=[validate_bitcoin_address],
        blank=True,
        null=True)

    class Meta:
        ordering = ('merchant', 'currency')
        unique_together = ('merchant', 'currency')

    def __unicode__(self):
        return u'{0} - {1}'.format(
            str(self.merchant),
            self.currency.name)

    @property
    def bitcoin_network(self):
        if self.currency.name == 'BTC':
            return 'mainnet'
        elif self.currency.name == 'TBTC':
            return 'testnet'
        else:
            # Instantfiat services work only with mainnet
            return 'mainnet'


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
        storage=VerificationFileStorage(),
        upload_to=verification_file_path_gen)
    uploaded = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=VERIFICATION_STATUSES, default='uploaded')
    gocoin_document_id = models.CharField(max_length=36, blank=True, null=True)
    comment = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = 'KYC document'

    def __unicode__(self):
        return u'{0} - {1}'.format(
            self.merchant.company_name,
            self.get_document_type_display())

    @property
    def base_name(self):
        return os.path.basename(self.file.name)

    @property
    def original_name(self):
        return get_verification_file_name(self.file)


def gen_batch_number():
    return uuid.uuid4().hex


class DeviceBatch(models.Model):

    batch_number = models.CharField(
        max_length=32,
        editable=False,
        unique=True,
        default=gen_batch_number)
    created_at = models.DateTimeField(auto_now_add=True)
    size = models.IntegerField()
    comment = models.TextField(blank=True)

    class Meta:
        verbose_name = 'batch'
        verbose_name_plural = 'device batches'

    def __unicode__(self):
        return self.batch_number


def gen_device_key():
    bts = uuid.uuid4().bytes
    return base58.encode(bts)[:8]


def get_default_batch():
    return DeviceBatch.objects.get(
        batch_number=settings.DEFAULT_BATCH_NUMBER).pk


class Device(models.Model):

    DEVICE_TYPES = [
        ('hardware', _('Terminal')),
        ('mobile', _('Mobile app')),
        ('web', _('Web app')),
    ]
    DEVICE_STATUSES = [
        ('registered', _('Registered')),
        ('activation', _('Activation in progress')),
        ('active', _('Operational')),
        ('suspended', _('Suspended')),
    ]
    PAYMENT_PROCESSING_CHOICES = [
        ('keep', _('keep bitcoins')),
        ('partially', _('convert partially')),
        ('full', _('convert full amount')),
    ]

    merchant = models.ForeignKey(MerchantAccount,
                                 blank=True,
                                 null=True)
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPES)
    status = FSMField(max_length=50,
                      choices=DEVICE_STATUSES,
                      default='registered',
                      protected=True)
    name = models.CharField(_('Your reference'), max_length=100)
    batch = models.ForeignKey(DeviceBatch, default=get_default_batch)
    key = models.CharField(_('Device key'),
                           max_length=64,
                           unique=True,
                           default=gen_device_key)
    activation_code = models.CharField(max_length=6,
                                       editable=False,
                                       unique=True)
    # TODO: remove serial number
    serial_number = models.CharField(max_length=50, blank=True, null=True)

    api_key = models.TextField(
        blank=True,
        null=True,
        validators=[validate_public_key],
        help_text='API public key')

    percent = models.DecimalField(
        _('Percent to convert'),
        max_digits=4,
        decimal_places=1,
        validators=[validate_percent],
        default=100)
    bitcoin_address = models.CharField(
        _('Bitcoin address to send to'),
        max_length=100,
        blank=True)
    bitcoin_network = models.CharField(
        max_length=50,
        choices=BITCOIN_NETWORKS,
        default='mainnet')
    our_fee_override = models.CharField(
        max_length=50,
        blank=True,
        null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(blank=True, null=True)
    last_reconciliation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']

    def __unicode__(self):
        return self.name

    def can_activate(self):
        return self.merchant is not None

    @transition(field=status,
                source='registered',
                target='activation',
                conditions=[can_activate])
    def start_activation(self):
        pass

    @transition(field=status,
                source=['activation', 'suspended'],
                target='active')
    def activate(self):
        pass

    @transition(field=status,
                source='active',
                target='suspended')
    def suspend(self):
        pass

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
        return self.paymentorder_set.filter(time_notified__isnull=False)

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
        return self.paymentorder_set.filter(time_notified__range=(beg, end))

    def is_online(self):
        if self.last_activity is None:
            return False
        delta = timezone.now() - self.last_activity
        return delta < datetime.timedelta(minutes=2)

    is_online.boolean = True

    @property
    def our_fee_address(self):
        if self.our_fee_override:
            return self.our_fee_override
        if self.bitcoin_network == 'mainnet':
            return config.OUR_FEE_MAINNET_ADDRESS
        elif self.bitcoin_network == 'testnet':
            return config.OUR_FEE_TESTNET_ADDRESS


@receiver(pre_save, sender=Device)
def device_generate_activation_code(sender, instance, **kwargs):
    if not instance.pk:
        # Generate unique activation code
        chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZ'
        while True:
            code = ''.join(random.sample(chars, 6))
            if not sender.objects.filter(activation_code=code).exists():
                instance.activation_code = code
                break


class ReconciliationTime(models.Model):
    device = models.ForeignKey(Device, related_name="rectime_set")
    email = models.EmailField(max_length=254)
    time = models.TimeField()

    class Meta:
        ordering = ['time']


# TODO: remove this functions

def gen_payment_reference():
    bts = uuid.uuid4().bytes
    return base58.encode(bts)[:10].upper()


def gen_payment_uid():
    bts = uuid.uuid4().bytes
    return base58.encode(bts)[:6]


def gen_withdrawal_uid():
    bts = uuid.uuid4().bytes
    return base58.encode(bts)[:6]

import datetime
from decimal import Decimal
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
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from constance import config
from django_countries.fields import CountryField
from django_fsm import FSMField, transition
from extended_choices import Choices
from localflavor.generic.models import BICField, IBANField
from slugify import slugify

from website.validators import (
    validate_phone,
    validate_post_code,
    validate_name,
    validate_bitcoin_address,
    validate_public_key)
from website.utils.files import (
    get_verification_file_name,
    verification_file_path_gen)


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
    amount_1 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text=_('Default value for payment amount button 1.'))
    amount_2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('2.50'),
        help_text=_('Default value for payment amount button 2.'))
    amount_3 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('10.00'),
        help_text=_('Default value for payment amount button 3.'))
    amount_shift = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.05'),
        help_text=_('Default value for payment amount shift button.'))

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


INSTANTFIAT_PROVIDERS = Choices(
    ('CRYPTOPAY', 1, 'CryptoPay'),
    ('GOCOIN', 2, 'GoCoin'),
)

KYC_DOCUMENT_TYPES = Choices(
    ('ID_FRONT', 1, 'ID document - frontside'),
    ('ADDRESS', 2, 'Address document'),
    ('ID_BACK', 3, 'ID document - backside'),
)


class MerchantAccount(models.Model):

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

    contact_first_name = models.CharField(
        _('Contact first name'),
        max_length=255,
        validators=[validate_name])
    contact_last_name = models.CharField(
        _('Contact last name'),
        max_length=255,
        validators=[validate_name])
    contact_phone = models.CharField(_('Contact phone'), max_length=32, validators=[validate_phone], null=True)
    contact_email = models.EmailField(_('Contact email'), max_length=254, unique=True)

    # Display language
    language = models.ForeignKey(Language, default=1)  # by default, English, see fixtures
    # Display currency
    currency = models.ForeignKey(Currency, default=1)  # by default, GBP, see fixtures
    ui_theme = models.ForeignKey(UITheme, default=1)  # 'default' theme, see fixtures

    instantfiat_provider = models.PositiveSmallIntegerField(
        _('InstantFiat provider'),
        choices=INSTANTFIAT_PROVIDERS,
        blank=True,
        null=True)
    instantfiat_merchant_id = models.CharField(
        _('InstantFiat merchant ID'),
        max_length=50,
        blank=True,
        null=True)
    instantfiat_email = models.EmailField(
        _('InstantFiat merchant email'),
        blank=True,
        null=True)
    instantfiat_api_key = models.CharField(
        _('InstantFiat API key'),
        max_length=200,
        blank=True,
        null=True)

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

    @property
    def has_managed_cryptopay_profile(self):
        return (self.instantfiat_provider ==
                INSTANTFIAT_PROVIDERS.CRYPTOPAY and
                self.instantfiat_merchant_id)

    def get_cryptopay_email(self):
        """
        Get email address for CryptoPay registration
        """
        if config.CRYPTOPAY_USE_FAKE_EMAIL:
            return 'merchant-{0}-{1}@xbterminal.io'.format(
                self.pk,
                slugify(self.company_name))
        else:
            return self.user.email

    def get_kyc_document(self, document_type, status):
        """
        Get latest KYC document for given status
        """
        try:
            return self.kycdocument_set.\
                filter(document_type=document_type, status=status).\
                latest('uploaded_at')
        except KYCDocument.DoesNotExist:
            return None

    def get_current_kyc_document(self, document_type):
        """
        Get currently active KYC document
        """
        return self.kycdocument_set.\
            filter(document_type=document_type).\
            exclude(status='uploaded').\
            latest('uploaded_at')

    @property
    def info(self):
        if not self.has_managed_cryptopay_profile or \
                self.verification_status == 'verified':
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
    max_payout = models.DecimalField(
        _('Maximum payout'),
        max_digits=20,
        decimal_places=8,
        default=0)
    forward_address = models.CharField(
        max_length=35,
        validators=[validate_bitcoin_address],
        blank=True,
        null=True)
    instantfiat = models.BooleanField()
    instantfiat_account_id = models.CharField(
        _('InstantFiat account ID'),
        max_length=50,
        blank=True,
        null=True)
    bank_account_name = models.CharField(
        max_length=255,
        blank=True,
        null=True)
    bank_account_bic = BICField(
        _('Bank account BIC'),
        blank=True,
        null=True)
    bank_account_iban = IBANField(
        _('Bank account IBAN'),
        blank=True,
        null=True)

    class Meta:
        ordering = ('merchant', 'instantfiat', 'currency')
        unique_together = ('merchant', 'currency')

    def __unicode__(self):
        if self.currency.name in ['BTC', 'TBTC']:
            balance_str = '{0:.8f}'.format(self.balance)
        else:
            balance_str = '{0:.2f}'.format(self.balance)
        return u'{name} - {balance}'.format(
            name=self.currency.name,
            balance=balance_str)

    @property
    def bitcoin_network(self):
        if self.currency.name == 'BTC':
            return 'mainnet'
        elif self.currency.name == 'TBTC':
            return 'testnet'
        else:
            # Instantfiat services work only with mainnet
            return 'mainnet'

    @property
    def balance(self):
        """
        Total balance on account, including unconfirmed deposits
        """
        result = self.transaction_set.aggregate(models.Sum('amount'))
        return result['amount__sum'] or Decimal('0.00000000')

    @property
    def balance_confirmed(self):
        """
        Amount available for withdrawal (inaccurate)
        """
        balance = Decimal('0.00000000')
        for transaction in self.transaction_set.all():
            if transaction.is_confirmed():
                balance += transaction.amount
        return balance

    @property
    def balance_min(self):
        return self.max_payout * self.device_set.count()

    @property
    def balance_max(self):
        multiplier = 3
        return self.balance_min * multiplier

    def get_transactions_by_date(self, range_beg, range_end):
        """
        Returns list of account transactions for date range
        Accepts:
            range_beg: beginning of range, datetime.date instance
            range_end: end of range, datetime.date instance
        """
        beg = timezone.make_aware(
            datetime.datetime.combine(range_beg, datetime.time.min),
            timezone.get_current_timezone())
        end = timezone.make_aware(
            datetime.datetime.combine(range_end, datetime.time.max),
            timezone.get_current_timezone())
        return self.transaction_set.\
            filter(created_at__range=(beg, end)).\
            order_by('created_at')

    def clean(self):
        if not hasattr(self, 'instantfiat'):
            return
        if self.instantfiat:
            if not self.instantfiat_account_id:
                raise ValidationError({
                    'instantfiat_account_id': 'This field is required.'})
        else:
            if not self.forward_address:
                raise ValidationError({
                    'forward_address': 'This field is required.'})


class Address(models.Model):

    account = models.ForeignKey(Account)
    address = models.CharField(
        max_length=35,
        unique=True,
        validators=[validate_bitcoin_address])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['account']
        verbose_name_plural = 'addresses'

    def __unicode__(self):
        return self.address


class Transaction(models.Model):

    payment = models.ForeignKey(
        'operations.PaymentOrder',
        blank=True,
        null=True)
    withdrawal = models.ForeignKey(
        'operations.WithdrawalOrder',
        blank=True,
        null=True)

    account = models.ForeignKey(Account)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    instantfiat_tx_id = models.CharField(
        _('InstantFiat transaction ID'),
        max_length=64,
        blank=True,
        null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['account', 'instantfiat_tx_id']

    def __unicode__(self):
        return str(self.pk)

    @property
    def tx_hash(self):
        if self.payment:
            return self.payment.outgoing_tx_id
        elif self.withdrawal:
            return self.withdrawal.outgoing_tx_id

    def is_confirmed(self):
        """
        If true, transaction will be included in calculation of
        confirmed balance of the account
        """
        # TODO: add is_confirmed field to Transaction model for accuracy
        if self.payment:
            return self.payment.time_confirmed is not None
        elif self.withdrawal:
            # Always include negative balance changes
            # 'broadcasted' means confidence reached, but not confirmed
            return (self.amount < 0 or
                    self.withdrawal.time_broadcasted is not None)
        else:
            # Transaction is not linked to operation, may be unconfirmed
            return True
    is_confirmed.boolean = True


class KYCDocument(models.Model):

    VERIFICATION_STATUSES = [
        ('uploaded', _('Uploaded')),
        ('unverified', _('Unverified')),
        ('denied', _('Denied')),
        ('verified', _('Verified')),
    ]

    merchant = models.ForeignKey(MerchantAccount)
    document_type = models.PositiveSmallIntegerField(
        choices=KYC_DOCUMENT_TYPES)
    file = models.FileField(
        upload_to=verification_file_path_gen)
    status = models.CharField(
        max_length=50,
        choices=VERIFICATION_STATUSES,
        default='uploaded')
    instantfiat_document_id = models.CharField(
        max_length=36,
        blank=True,
        null=True)
    comment = models.CharField(
        max_length=255,
        blank=True,
        null=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

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


@receiver(post_delete, sender=KYCDocument)
def kyc_document_delete(sender, instance, **kwargs):
    instance.file.delete(save=False)


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
        ('activation_in_progress', _('Activation in progress')),
        ('activation_error', _('Activation error')),
        ('active', _('Operational')),
        ('suspended', _('Suspended')),
    ]

    merchant = models.ForeignKey(
        MerchantAccount,
        blank=True,
        null=True)
    account = models.ForeignKey(
        Account,
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

    api_key = models.TextField(
        blank=True,
        null=True,
        validators=[validate_public_key],
        help_text='API public key')
    # TODO: remove field
    our_fee_override = models.CharField(
        max_length=50,
        blank=True,
        null=True)

    # GUI config
    amount_1 = models.DecimalField(
        max_digits=12, decimal_places=2,
        blank=True, null=True)
    amount_2 = models.DecimalField(
        max_digits=12, decimal_places=2,
        blank=True, null=True)
    amount_3 = models.DecimalField(
        max_digits=12, decimal_places=2,
        blank=True, null=True)
    amount_shift = models.DecimalField(
        max_digits=12, decimal_places=2,
        blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-id']

    def __unicode__(self):
        return self.name

    def can_activate(self):
        return self.merchant is not None and self.account is not None

    @transition(field=status,
                source='registered',
                target='activation_in_progress',
                conditions=[can_activate])
    def start_activation(self):
        # Copy global defaults
        self.amount_1 = self.merchant.currency.amount_1
        self.amount_2 = self.merchant.currency.amount_2
        self.amount_3 = self.merchant.currency.amount_3
        self.amount_shift = self.merchant.currency.amount_shift
        self.save()

    @transition(field=status,
                source='activation_in_progress',
                target='activation_error')
    def set_activation_error(self):
        pass

    @transition(field=status,
                source=['activation_in_progress', 'suspended'],
                target='active')
    def activate(self):
        pass

    @transition(field=status,
                source='active',
                target='suspended')
    def suspend(self):
        pass

    @property
    def bitcoin_network(self):
        if self.account:
            return self.account.bitcoin_network
        else:
            return 'mainnet'

    def get_transactions(self):
        """
        Returns list of device transactions
        """
        return Transaction.objects.filter(
            models.Q(payment__device=self) |
            models.Q(withdrawal__device=self)).order_by('created_at')

    def get_transactions_by_date(self, range_beg, range_end):
        """
        Returns list of device transactions for date range
        Accepts:
            range_beg: beginning of range, datetime.date instance
            range_end: end of range, datetime.date instance
        """
        beg = timezone.make_aware(
            datetime.datetime.combine(range_beg, datetime.time.min),
            timezone.get_current_timezone())
        end = timezone.make_aware(
            datetime.datetime.combine(range_end, datetime.time.max),
            timezone.get_current_timezone())
        return self.get_transactions().\
            filter(created_at__range=(beg, end)).\
            order_by('created_at')

    def is_online(self):
        if self.last_activity is None:
            return False
        delta = timezone.now() - self.last_activity
        return delta < datetime.timedelta(minutes=2)

    is_online.boolean = True


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

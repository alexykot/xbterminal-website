import datetime

from django import forms
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm as DjangoAuthenticationForm,
    UserCreationForm as DjangoUserCreationForm,
    UserChangeForm as DjangoUserChangeForm)
from django.db.models import Q
from django.db.transaction import atomic
from django.utils.translation import ugettext as _

from captcha.fields import ReCaptchaField
from constance import config
from oauth2_provider.models import Application

from website.models import (
    Currency,
    User,
    MerchantAccount,
    Account,
    Device,
    KYCDocument,
    get_language,
    get_currency,
    INSTANTFIAT_PROVIDERS,
    KYC_DOCUMENT_TYPES)
from website.widgets import (
    FileWidget,
    ForeignKeyWidget)
from website.validators import validate_bitcoin_address
from website.utils.email import (
    send_registration_email,
    send_reset_password_email)
from operations.exceptions import CryptoPayUserAlreadyExists
from operations.instantfiat import cryptopay


class UserCreationForm(DjangoUserCreationForm):

    class Meta:
        model = User
        fields = ['email']


class UserChangeForm(DjangoUserChangeForm):

    class Meta:
        model = User
        fields = '__all__'


class AuthenticationForm(DjangoAuthenticationForm):

    def clean_username(self):
        email = self.cleaned_data['username']
        return email.lower()


class LoginMethodForm(forms.Form):
    """
    Choose how to login
    """
    method = forms.ChoiceField(
        label='',
        choices=(
            ('login', _('Log in as existing merchant')),
            ('register', _('Register a new merchant')),
        ),
        widget=forms.RadioSelect,
        error_messages={
            'required': _('Please choose how to login.'),
        })


class ResetPasswordForm(forms.Form):

    email = forms.EmailField()

    def __init__(self, *args, **kwargs):
        super(ResetPasswordForm, self).__init__(*args, **kwargs)
        self._user = None

    def clean_email(self):
        email = self.cleaned_data['email']
        user_model = get_user_model()
        try:
            self._user = user_model.objects.get(email=email)
        except user_model.DoesNotExist:
            raise forms.ValidationError(_('No user with such email exists'))
        return email

    def set_new_password(self):
        password = get_user_model().objects.make_random_password()
        self._user.set_password(password)
        send_reset_password_email(self.cleaned_data['email'], password)
        self._user.save()


class CaptchaMixin(object):
    """
    Adds captcha to form
    """
    MAX_SUBMISSIONS = 3
    CACHE_KEY_TEMPLATE = 'form-{ip}'

    def __init__(self, *args, **kwargs):
        user_ip = kwargs.pop('user_ip')
        super(CaptchaMixin, self).__init__(*args, **kwargs)
        assert 'captcha' in self.fields
        if user_ip:
            cache_key = self.CACHE_KEY_TEMPLATE.format(ip=user_ip)
            submit_count = cache.get(cache_key, 0)
            if submit_count < self.MAX_SUBMISSIONS:
                # Dont show captcha for first N submits
                del self.fields['captcha']
            if self.is_bound:
                # Update counter when form is submitted
                submit_count += 1
                cache.set(cache_key, submit_count, timeout=None)


class ContactForm(CaptchaMixin, forms.Form):
    """
    Simple contact form
    """
    CACHE_KEY_TEMPLATE = 'form-contact-{ip}'

    email = forms.EmailField()
    name = forms.CharField()
    company_name = forms.CharField(required=False)
    message = forms.CharField(widget=forms.Textarea)
    captcha = ReCaptchaField(attrs={'theme': 'clean'})


class FeedbackForm(CaptchaMixin, forms.Form):
    """
    Simple feedback form
    """
    CACHE_KEY_TEMPLATE = 'form-feedback-{ip}'

    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)
    captcha = ReCaptchaField(attrs={'theme': 'clean'})


class SubscribeForm(forms.Form):
    """
    Subscribe to newsletters
    """
    email = forms.EmailField()


class SimpleMerchantRegistrationForm(forms.ModelForm):
    """
    Merchant registration form (simplified)
    """
    class Meta:
        model = MerchantAccount
        fields = [
            'company_name',
            'country',
            'contact_first_name',
            'contact_last_name',
            'contact_email',
        ]

    def clean(self):
        """
        Trim whitespaces for all text fields
        """
        cleaned_data = super(SimpleMerchantRegistrationForm, self).clean()
        for key, value in cleaned_data.items():
            if isinstance(value, basestring):
                cleaned_data[key] = value.strip()
        return cleaned_data

    @atomic
    def save(self):
        """
        Create django user and merchant account
        """
        merchant = super(SimpleMerchantRegistrationForm, self).save(commit=False)
        merchant.language = get_language(merchant.country.code)
        merchant.currency = get_currency(merchant.country.code)
        # Create new user
        password = get_user_model().objects.make_random_password()
        user = get_user_model().objects.create_user(
            merchant.contact_email,
            password,
            commit=False)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        user.save()
        # Create merchant
        merchant.user = user
        merchant.save()
        # Create oauth client
        Application.objects.create(
            user=user,
            name='XBTerminal app',
            client_id=user.email,
            client_type='confidential',
            authorization_grant_type='password',
            client_secret='AFoUFXG8orJ2H5ztnycc5a95')
        # Create internal BTC account
        Account.objects.create(
            merchant=merchant,
            currency=Currency.objects.get(name='BTC'),
            instantfiat=False)
        # Perform registration on CryptoPay
        merchant.instantfiat_provider = INSTANTFIAT_PROVIDERS.CRYPTOPAY
        merchant.instantfiat_email = merchant.get_cryptopay_email()
        try:
            merchant.instantfiat_merchant_id = cryptopay.create_merchant(
                merchant.contact_first_name,
                merchant.contact_last_name,
                merchant.instantfiat_email,
                config.CRYPTOPAY_API_KEY)
        except CryptoPayUserAlreadyExists:
            pass
        merchant.save()
        # Send email
        send_registration_email(merchant.contact_email, password)
        return merchant


class MerchantRegistrationForm(SimpleMerchantRegistrationForm):
    """
    Merchant registration form
    """
    terms = forms.BooleanField(
        label=_(
            'I agree to XBTerminal <a href="%(privacy_url)s" target="_blank">'
            'Privacy Policy</a> and <a href="%(terms_url)s" target="_blank">'
            'Terms & Conditions</a> of use.'
        ) % {
            'privacy_url': '/privacy/',
            'terms_url': '/terms/',
        },
        error_messages={
            'required': _('Please accept terms & conditions.'),
        })

    class Meta:
        model = MerchantAccount
        fields = [
            'company_name',
            'trading_name',
            'business_address',
            'business_address1',
            'town',
            'county',
            'post_code',
            'country',
            'contact_first_name',
            'contact_last_name',
            'contact_phone',
            'contact_email',
        ]
        labels = {
            'business_address': _('Trading address'),
            'post_code': _('Post code/Zip code'),
            'contact_first_name': _('First name'),
            'contact_last_name': _('Last name'),
            'contact_email': _('Email'),
        }


class ProfileForm(forms.ModelForm):

    class Meta:
        model = MerchantAccount
        fields = [
            'company_name',
            'trading_name',
            'business_address',
            'business_address1',
            'town',
            'county',
            'post_code',
            'country',
            'contact_first_name',
            'contact_last_name',
            'contact_phone',
            'contact_email',
        ]
        labels = {
            'business_address': _('Trading address'),
            'contact_first_name': _('First name'),
            'contact_last_name': _('Last name'),
            'contact_email': _('Email'),
            'contact_phone': _('Phone'),
        }

    def clean(self):
        """
        Trim whitespaces for all fields
        """
        cleaned_data = super(ProfileForm, self).clean()
        return {key: val.strip() for key, val in cleaned_data.items()}

    def save(self, commit=True):
        instance = super(ProfileForm, self).save(commit=False)
        instance.language = get_language(instance.country.code)
        instance.currency = get_currency(instance.country.code)
        if commit:
            instance.save()
        return instance


class InstantFiatSettingsForm(forms.ModelForm):

    class Meta:
        model = MerchantAccount
        fields = [
            'instantfiat_provider',
            'instantfiat_api_key',
        ]
        widgets = {
            'instantfiat_provider': forms.HiddenInput,
        }
        labels = {
            'instantfiat_api_key': 'CryptoPay API key',
        }

    def __init__(self, *args, **kwargs):
        super(InstantFiatSettingsForm, self).__init__(*args, **kwargs)
        self.fields['instantfiat_api_key'].required = True

    def clean_instantfiat_provider(self):
        return INSTANTFIAT_PROVIDERS.CRYPTOPAY


class KYCDocumentUploadForm(forms.ModelForm):

    class Meta:
        model = KYCDocument
        fields = ['file']
        widgets = {'file': FileWidget}

    def __init__(self, *args, **kwargs):
        self.document_type = kwargs.pop('document_type', None)
        super(KYCDocumentUploadForm, self).__init__(*args, **kwargs)
        if self.document_type == KYC_DOCUMENT_TYPES.ID_FRONT:
            self.fields['file'].label = _('Photo ID (front side)')
        elif self.document_type == KYC_DOCUMENT_TYPES.ID_BACK:
            self.fields['file'].label = _('Photo ID (back side)')
        elif self.document_type == KYC_DOCUMENT_TYPES.ADDRESS:
            self.fields['file'].label = _('Corporate or residence proof document')


class DeviceForm(forms.ModelForm):

    class Meta:
        model = Device
        fields = [
            'device_type',
            'name',
            'account',
        ]
        widgets = {
            'device_type': forms.HiddenInput,
        }

    class Media:
        js = ['js/device-form.js']

    def __init__(self, *args, **kwargs):
        self.merchant = kwargs.pop('merchant')
        super(DeviceForm, self).__init__(*args, **kwargs)
        self.fields['account'].queryset = self.merchant.account_set.\
            filter(
                Q(instantfiat=True, currency=self.merchant.currency) |
                Q(instantfiat=False))
        self.fields['account'].required = True

    def device_type_verbose(self):
        device_types = dict(Device.DEVICE_TYPES)
        device_type = self['device_type'].value()
        return str(device_types[device_type])

    def save(self, commit=True):
        device = super(DeviceForm, self).save(commit=False)
        if device.status == 'registered':
            device.merchant = self.merchant
            device.start_activation()
            device.activate()
        if commit:
            device.save()
        return device


class DeviceActivationForm(forms.Form):

    activation_code = forms.CharField()

    def clean_activation_code(self):
        activation_code = self.cleaned_data['activation_code'].upper().strip()
        try:
            self.device = Device.objects.get(
                activation_code=activation_code,
                status='registered')
        except Device.DoesNotExist:
            raise forms.ValidationError('Invalid activation code.')
        return activation_code


class DeviceAdminForm(forms.ModelForm):

    class Meta:
        model = Device
        fields = '__all__'
        widgets = {
            'merchant': ForeignKeyWidget(model=MerchantAccount),
        }

    def __init__(self, *args, **kwargs):
        super(DeviceAdminForm, self).__init__(*args, **kwargs)
        if self.instance.pk and self.instance.merchant:
            # django.contrib.admin.widgets.RelatedFieldWidgetWrapper
            self.fields['merchant'].widget.widget.attrs['disabled'] = 'disabled'
            self.fields['account'].queryset = self.instance.\
                merchant.account_set.all()

    def clean(self):
        cleaned_data = super(DeviceAdminForm, self).clean()
        account = cleaned_data.get('account')
        if account:
            addresses = ['our_fee_override']
            for address in addresses:
                try:
                    if cleaned_data[address]:
                        validate_bitcoin_address(
                            cleaned_data[address],
                            network=account.bitcoin_network)
                except forms.ValidationError as error:
                    for error_message in error.messages:
                        self.add_error(address, error_message)
        return cleaned_data


class AccountForm(forms.ModelForm):

    class Meta:
        model = Account
        fields = [
            'currency',
            'max_payout',
            'forward_address',
        ]

    def __init__(self, *args, **kwargs):
        super(AccountForm, self).__init__(*args, **kwargs)
        assert self.instance and self.instance.pk
        self.fields['currency'].widget.attrs['disabled'] = True
        self.fields['currency'].required = False
        if self.instance.currency.name not in ['BTC', 'TBTC']:
            del self.fields['max_payout']
            del self.fields['forward_address']

    def clean_currency(self):
        return self.instance.currency

    def clean(self):
        cleaned_data = super(AccountForm, self).clean()
        forward_address = cleaned_data.get('forward_address')
        if forward_address:
            try:
                validate_bitcoin_address(
                    forward_address,
                    network=self.instance.bitcoin_network)
            except forms.ValidationError as error:
                for error_message in error.messages:
                    self.add_error('forward_address', error_message)
        return cleaned_data


class TransactionSearchForm(forms.Form):

    WIDGET_ATTRS = {
        'data-provide': 'datepicker',
        'data-date-format': 'yyyy-mm-dd',
        'data-date-autoclose': 'true',
    }

    range_beg = forms.DateField(
        label=_('From'),
        initial=datetime.date.today,
        widget=forms.TextInput(attrs=WIDGET_ATTRS))
    range_end = forms.DateField(
        label=_('To'),
        initial=datetime.date.today,
        widget=forms.TextInput(attrs=WIDGET_ATTRS))

    def clean(self):
        cleaned_data = super(TransactionSearchForm, self).clean()
        range_beg = cleaned_data.get('range_beg')
        range_end = cleaned_data.get('range_end')
        if range_beg and range_end and range_end < range_beg:
            self.add_error(
                'range_end',
                'Second date must not be earlier than the first.')
        return cleaned_data

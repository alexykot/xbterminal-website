from django import forms
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm as DjangoAuthenticationForm,
    UserCreationForm as DjangoUserCreationForm,
    UserChangeForm as DjangoUserChangeForm)
from django.utils.translation import ugettext as _

from constance import config
from captcha.fields import ReCaptchaField
from oauth2_provider.models import Application

from operations import preorder
from operations.instantfiat import gocoin  # flake8: noqa

from website.models import (
    Currency,
    User,
    MerchantAccount,
    Account,
    Device,
    ReconciliationTime,
    KYCDocument,
    get_language,
    get_currency)
from website.widgets import (
    ButtonGroupRadioSelect,
    PercentWidget,
    TimeWidget,
    FileWidget,
    ForeignKeyWidget)
from website.validators import validate_bitcoin_address
from website.utils import create_html_message
from operations.models import Order


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
        email = create_html_message(
            _("Reset password for xbterminal.io"),
            'email/reset_password.html',
            {'password': password},
            settings.DEFAULT_FROM_EMAIL,
            [self.cleaned_data['email']])
        email.send(fail_silently=False)
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
        Trim whitespaces for all fields
        """
        cleaned_data = super(SimpleMerchantRegistrationForm, self).clean()
        return {key: val.strip() for key, val in cleaned_data.items()}

    def save(self, commit=True):
        """
        Create django user and merchant account
        """
        assert commit  # Always commit
        instance = super(SimpleMerchantRegistrationForm, self).save(commit=False)
        instance.language = get_language(instance.country.code)
        instance.currency = get_currency(instance.country.code)
        # Create GoCoin account (disabled)
        # instance.gocoin_merchant_id = gocoin.create_merchant(instance, config.GOCOIN_AUTH_TOKEN)
        # Create new user
        password = get_user_model().objects.make_random_password()
        user = get_user_model().objects.create_user(
            instance.contact_email,
            password,
            commit=False)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        # Send email
        message = create_html_message(
            _("Registration for XBTerminal.io"),
            "email/registration.html",
            {'email': instance.contact_email,
             'password': password},
            settings.DEFAULT_FROM_EMAIL,
            [instance.contact_email])
        message.send(fail_silently=False)
        # Save objects
        user.save()
        instance.user = user
        instance.save()
        # Create oauth client
        Application.objects.create(
            user=user,
            name='XBTerminal app',
            client_id=user.email,
            client_type='confidential',
            authorization_grant_type='password',
            client_secret='AFoUFXG8orJ2H5ztnycc5a95')
        # Create BTC account
        Account.objects.create(
            merchant=instance,
            currency=Currency.objects.get(name='BTC'))
        return instance


class MerchantRegistrationForm(SimpleMerchantRegistrationForm):
    """
    Merchant registration form
    """
    regtype = forms.ChoiceField(
        choices=[
            ('default', 'default'),
            ('terminal', 'terminal'),
            ('web', 'web'),
        ],
        widget=forms.HiddenInput)

    # Used at registration step 1
    company_name_copy = forms.CharField(
        label=_('Company name'),
        required=False)

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


class TerminalOrderForm(forms.ModelForm):
    """
    Terminal order form
    """
    delivery_address_differs = forms.BooleanField(
        label=_("Deliver to a different address"),
        required=False)

    class Meta:
        model = Order
        exclude = [
            'merchant',
            'created',
            'fiat_total_amount',
            'delivery_address2',
            'delivery_contact_phone',
            'instantfiat_invoice_id',
            'instantfiat_btc_total_amount',
            'instantfiat_address',
            'payment_reference',
            'payment_status',
        ]
        labels = {
            'quantity': _('Terminals on order'),
            'delivery_town': _('Town'),
            'delivery_post_code': _('Post code/Zip code'),
            'delivery_county': _('State / County'),
            'delivery_country': _('Country'),
        }
        widgets = {
            'quantity': forms.TextInput,
            'payment_method': ButtonGroupRadioSelect,
        }

    @property
    def terminal_price(self):
        return preorder.get_terminal_price()

    @property
    def exchange_rate(self):
        return preorder.get_exchange_rate()

    def clean(self):
        cleaned_data = super(TerminalOrderForm, self).clean()
        if cleaned_data.get('delivery_address_differs'):
            required_fields = [
                'delivery_address',
                'delivery_town',
                'delivery_post_code',
                'delivery_country',
            ]
            for field_name in required_fields:
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, _('This field is required.'))
        return cleaned_data

    def save(self, merchant, commit=True):
        assert commit  # Always commit
        instance = super(TerminalOrderForm, self).save(commit=False)
        instance.merchant = merchant
        instance.fiat_total_amount = instance.quantity * self.terminal_price * 1.2
        if not self.cleaned_data.get('delivery_address_differs'):
            # Copy address fields from merchant instance
            instance.delivery_address = merchant.business_address
            instance.delivery_address1 = merchant.business_address1
            instance.delivery_town = merchant.town
            instance.delivery_county = merchant.county
            instance.delivery_post_code = merchant.post_code
            instance.delivery_country = merchant.country
            instance.delivery_contact_phone = merchant.contact_phone
        instance.save()
        if instance.payment_method == "bitcoin":
            preorder.create_invoice(instance)
        return instance


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
        # if instance.gocoin_merchant_id:
            # merchants = gocoin.get_merchants(config.GOCOIN_MERCHANT_ID,
                                             # config.GOCOIN_AUTH_TOKEN)
            # if instance.gocoin_merchant_id in merchants:
                # gocoin.update_merchant(instance, config.GOCOIN_AUTH_TOKEN)
        if commit:
            instance.save()
        return instance


class KYCDocumentUploadForm(forms.ModelForm):

    class Meta:
        model = KYCDocument
        fields = ['file']
        widgets = {'file': FileWidget}

    def __init__(self, *args, **kwargs):
        document_type = kwargs.pop('document_type', None)
        super(KYCDocumentUploadForm, self).__init__(*args, **kwargs)
        if document_type == 1:
            self.fields['file'].label = _('Photo ID')
        elif document_type == 2:
            self.fields['file'].label = _('Corporate or residence proof document')


class DeviceForm(forms.ModelForm):

    payment_processing = forms.ChoiceField(
        label=_('Payment processing'),
        choices=Device.PAYMENT_PROCESSING_CHOICES,
        widget=ButtonGroupRadioSelect,
        initial='keep')

    class Meta:
        model = Device
        fields = [
            'device_type',
            'name',
            'payment_processing',
            'percent',
            'bitcoin_address',
        ]
        widgets = {
            'device_type': forms.HiddenInput,
            'percent': PercentWidget,
        }

    class Media:
        js = ['js/device-form.js']

    def device_type_verbose(self):
        device_types = dict(Device.DEVICE_TYPES)
        device_type = self['device_type'].value()
        return device_types[device_type]

    def clean(self):
        cleaned_data = super(DeviceForm, self).clean()
        try:
            percent = cleaned_data['percent']
            bitcoin_address = cleaned_data['bitcoin_address']
        except KeyError:
            return cleaned_data
        if percent < 100 and not bitcoin_address:
            self.add_error('bitcoin_address', 'This field is required.')
        if self.instance and bitcoin_address:
            try:
                validate_bitcoin_address(bitcoin_address,
                                         network=self.instance.bitcoin_network)
            except forms.ValidationError as error:
                for error_message in error.messages:
                    self.add_error('bitcoin_address', error_message)
        return cleaned_data


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

    def clean(self):
        cleaned_data = super(DeviceAdminForm, self).clean()
        addresses = ['bitcoin_address', 'our_fee_override']
        network = cleaned_data['bitcoin_network']
        for address in addresses:
            try:
                if cleaned_data[address]:
                    validate_bitcoin_address(cleaned_data[address],
                                             network=network)
            except forms.ValidationError as error:
                for error_message in error.messages:
                    self.add_error(address, error_message)
        return cleaned_data


class SendReconciliationForm(forms.Form):
    email = forms.EmailField()
    date = forms.DateField(widget=forms.HiddenInput)


class SendDailyReconciliationForm(forms.ModelForm):
    time = forms.TimeField(input_formats=['%I:%M %p'],
                           widget=TimeWidget(format='%I:%M %p'))

    class Meta:
        model = ReconciliationTime
        fields = ['email', 'time']

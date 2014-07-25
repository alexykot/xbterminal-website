from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm as DjangoAuthenticationForm
from django.core.mail import send_mail
from django.core.validators import RegexValidator
from django.template.loader import render_to_string

from website.models import MerchantAccount, Device, ReconciliationTime, Order
from website.fields import BCAddressField
from website.widgets import ButtonGroupRadioSelect, PercentWidget, TimeWidget


class ContactForm(forms.Form):
    """
    Simple contact form
    """
    email = forms.EmailField()
    name = forms.CharField()
    company_name = forms.CharField(required=False)
    message = forms.CharField(widget=forms.Textarea)


class SubscribeForm(forms.Form):
    """
    Subscribe to newsletters
    """
    email = forms.EmailField()


class MerchantRegistrationForm(forms.ModelForm):
    """
    Merchant registration form
    """
    regtype = forms.ChoiceField(
        choices=[('default', 'default'), ('terminal', 'terminal')],
        widget=forms.HiddenInput)

    class Meta:
        model = MerchantAccount
        exclude = ['user', 'language', 'currency']

    def save(self, commit=True):
        """
        Create django user and merchant account
        """
        assert commit  # Always commit
        instance = super(MerchantRegistrationForm, self).save(commit=False)
        user_model = get_user_model()
        password = user_model.objects.make_random_password()
        email = self.cleaned_data['contact_email']
        # Send email
        mail_text = render_to_string(
            "website/email/registration.txt",
            {'email': email, 'password': password})
        send_mail("Registration on xbterminal.io",
                  mail_text,
                  settings.DEFAULT_FROM_EMAIL,
                  [email],
                  fail_silently=False)
        # Create new user
        user = user_model.objects.create_user(email, email, password)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        instance.user = user
        instance.save()
        return instance


class TerminalOrderForm(forms.ModelForm):
    """
    Terminal order form
    """
    delivery_address_differs = forms.BooleanField(
        label="Delivery address differs from business address",
        required=False)

    class Meta:
        model = Order
        exclude = ['merchant']
        labels = {'quantity': 'Amount of terminals to order'}
        widgets = {'payment_method': forms.RadioSelect}

    def clean(self):
        cleaned_data = super(TerminalOrderForm, self).clean()
        if cleaned_data.get('delivery_address_differs'):
            required_fields = [
                'delivery_address',
                'delivery_town',
                'delivery_post_code',
                'delivery_country',
                'delivery_contact_phone',
            ]
            blank_fields = ', '.join(name for name in required_fields
                                     if not cleaned_data.get(name))
            if blank_fields:
                raise forms.ValidationError(
                    "This fields are required: {0}".format(blank_fields))
        return cleaned_data

    def save(self, merchant, commit=True):
        instance = super(TerminalOrderForm, self).save(commit=False)
        instance.merchant = merchant
        if not self.cleaned_data.get('delivery_address_differs'):
            # Copy address fields from merchant instance
            instance.delivery_address = merchant.business_address
            instance.delivery_address1 = merchant.business_address1
            instance.delivery_address2 = merchant.business_address2
            instance.delivery_town = merchant.town
            instance.delivery_county = merchant.county
            instance.delivery_post_code = merchant.post_code
            instance.delivery_country = merchant.country
            instance.delivery_contact_phone = merchant.contact_phone
        if commit:
            instance.save()
        return instance


class AuthenticationForm(DjangoAuthenticationForm):

    def __init__(self, *args, **kwargs):
        super(AuthenticationForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'


class ProfileForm(forms.ModelForm):
    class Meta:
        model = MerchantAccount
        fields = ['company_name',
                  'business_address', 'business_address1', 'business_address2',
                  'town', 'country', 'post_code']


class DeviceForm(forms.ModelForm):

    bitcoin_address = BCAddressField(required=False)

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
            'payment_processing': ButtonGroupRadioSelect,
            'percent': PercentWidget,
        }

    class Media:
        js = ['js/device-form.js']

    def device_type_verbose(self):
        device_types = dict(Device.DEVICE_TYPES)
        device_type = self['device_type'].value()
        return device_types[device_type]

    def clean_percent(self):
        payment_processing = self.cleaned_data['payment_processing']
        percent = self.cleaned_data['percent']

        if payment_processing == 'partially' and not percent:
            raise forms.ValidationError('This field is required.')

        if payment_processing == 'full':
            percent = 100

        return percent

    def clean_bitcoin_address(self):
        payment_processing = self.cleaned_data['payment_processing']
        bitcoin_address = self.cleaned_data['bitcoin_address']

        if payment_processing in ['keep', 'partially'] and not bitcoin_address:
            raise forms.ValidationError('This field is required.')

        if bitcoin_address and self.instance:
            bitcoin_network = self.instance.bitcoin_network
            if bitcoin_network == 'mainnet' and bitcoin_address[0] not in ['1', '3']:
                raise forms.ValidationError('This field must starts with "1" or "3".')
            if bitcoin_network == 'testnet' and bitcoin_address[0] not in ['n', 'm']:
                raise forms.ValidationError('This field must starts with "n" or "m" on testnet.')

        return bitcoin_address


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = Device

    def clean(self):
        cleaned_data = super(DeviceAdminForm, self).clean()
        bitcoin_address = cleaned_data['bitcoin_address']
        bitcoin_network = cleaned_data['bitcoin_network']

        if bitcoin_address:
            if bitcoin_network == 'mainnet' and bitcoin_address[0] not in ['1', '3']:
                raise forms.ValidationError('This field must starts with "1" or "3" on mainnet.')
            if bitcoin_network == 'testnet' and bitcoin_address[0] not in ['n', 'm']:
                raise forms.ValidationError('This field must starts with "n" or "m" on testnet.')

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


class EnterAmountForm(forms.Form):

    device_key = forms.CharField(
        validators=[RegexValidator('^[0-9a-fA-F]{32}$')])
    amount = forms.DecimalField(
        max_digits=9,
        decimal_places=2,
        min_value=Decimal('0.01'))
    bt_mac = forms.CharField(
        required=False,
        validators=[RegexValidator('^[0-9a-fA-F:]{17}$')])

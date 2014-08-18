from decimal import Decimal
import smtplib

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    UserCreationForm as DjangoUserCreationForm,
    UserChangeForm as DjangoUserChangeForm)
from django.core.mail import send_mail
from django.core.validators import RegexValidator
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from payment import preorder

from website.models import User, MerchantAccount, Device, ReconciliationTime, Order
from website.fields import BCAddressField
from website.widgets import ButtonGroupRadioSelect, PercentWidget, TimeWidget
from website.validators import validate_bitcoin_address


class UserCreationForm(DjangoUserCreationForm):

    def __init__(self, *args, **kargs):
        super(UserCreationForm, self).__init__(*args, **kargs)
        del self.fields['username']

    class Meta:
        model = User


class UserChangeForm(DjangoUserChangeForm):

    def __init__(self, *args, **kargs):
        super(UserChangeForm, self).__init__(*args, **kargs)
        del self.fields['username']

    class Meta:
        model = User


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
        exclude = ['user', 'business_address2', 'language', 'currency']
        labels = {
            'business_address': _('Trading address'),
            'post_code': _('Post code/Zip code'),
            'contact_first_name': _('First name'),
            'contact_last_name': _('Last name'),
            'contact_email': _('Email'),
        }

    def clean(self):
        cleaned_data = super(MerchantRegistrationForm, self).clean()
        self._password = get_user_model().objects.make_random_password()
        # Send email
        mail_text = render_to_string("website/email/registration.txt", {
            'email': cleaned_data['contact_email'],
            'password': self._password,
        })
        if not self._errors:
            try:
                send_mail("Registration for XBTerminal.io",
                        mail_text,
                        settings.DEFAULT_FROM_EMAIL,
                        [cleaned_data['contact_email']],
                        fail_silently=False)
            except smtplib.SMTPRecipientsRefused as error:
                self._errors['contact_email'] = self.error_class(['Invalid email.'])
                del cleaned_data['contact_email']
        return cleaned_data

    def save(self, commit=True):
        """
        Create django user and merchant account
        """
        assert commit  # Always commit
        instance = super(MerchantRegistrationForm, self).save(commit=False)
        # Create new user
        user = get_user_model().objects.create_user(
            self.cleaned_data['contact_email'],
            self._password)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        instance.user = user
        instance.save()
        return instance


class TerminalOrderForm(forms.ModelForm):
    """
    Terminal order form
    """
    delivery_address_differs = forms.BooleanField(
        label="Deliver to a different address",
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
            'quantity': 'Terminals on order',
            'delivery_town': 'Town',
            'delivery_post_code': 'Post code/Zip code',
            'delivery_county': 'State / County',
            'delivery_country': 'Country',
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
                    self._errors[field_name] = self.error_class(
                        ["This field is required."])
                    del cleaned_data[field_name]
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
        exclude = ['user', 'business_address2', 'language', 'currency']
        labels = {
            'business_address': 'Trading address',
            'contact_first_name': 'First name',
            'contact_last_name': 'Last name',
            'contact_email': 'Email',
            'contact_phone': 'Phone',
        }

class DeviceForm(forms.ModelForm):

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
        if payment_processing == 'keep':
            percent = 0
        elif payment_processing == 'full':
            percent = 100
        return percent

    def clean(self):
        cleaned_data = super(DeviceForm, self).clean()
        payment_processing = cleaned_data['payment_processing']
        bitcoin_address = cleaned_data['bitcoin_address']
        if payment_processing in ['keep', 'partially'] and not bitcoin_address:
            self._errors['bitcoin_address'] = self.error_class(["This field is required."])
            del cleaned_data['bitcoin_address']
        if self.instance and bitcoin_address:
            try:
                validate_bitcoin_address(bitcoin_address,
                                         network=self.instance.bitcoin_network)
            except forms.ValidationError as error:
                self._errors['bitcoin_address'] = self.error_class(error.messages)
                del cleaned_data['bitcoin_address']
        return cleaned_data


class DeviceAdminForm(forms.ModelForm):

    class Meta:
        model = Device

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
                self._errors[address] = self.error_class(error.messages)
                del cleaned_data[address]
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
        validators=[RegexValidator('^[0-9a-zA-Z]{8,32}$')])
    amount = forms.DecimalField(
        max_digits=9,
        decimal_places=2,
        min_value=Decimal('0.01'))
    bt_mac = forms.CharField(
        required=False,
        validators=[RegexValidator('^[0-9a-fA-F:]{17}$')])

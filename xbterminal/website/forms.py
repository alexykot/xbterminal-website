from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm as DjangoAuthenticationForm
from django.core import validators

from website.models import MerchantAccount, Device, ReconciliationTime
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
    class Meta:
        model = MerchantAccount
        exclude = ['user']
        widgets = {
            'country': forms.Select(attrs={'class': 'form-control'}),
        }


class AuthenticationForm(DjangoAuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        super(AuthenticationForm, self).__init__(*args, **kwargs)

        self.fields['username'].label = 'Email'


class ProfileForm(forms.ModelForm):
    class Meta:
        model = MerchantAccount
        fields = ('company_name', 'business_address', 'business_address1', 'business_address2',
                  'town', 'country', 'post_code')

    class Media:
        css = {'all': ('css/custom.css',)}


class DeviceForm(forms.ModelForm):
    payment_processor = forms.ChoiceField(
        choices=Device.PAYMENT_PROCESSOR_CHOICES,
        widget=ButtonGroupRadioSelect,
        required=False
    )
    bitcoin_address = BCAddressField(required=False)

    class Meta:
        model = Device
        fields = ('name', 'language', 'currency', 'comment', 'payment_processing', 'payment_processor',
                  'api_key', 'percent', 'bitcoin_address')
        widgets = {
            'payment_processing': ButtonGroupRadioSelect,
            'percent': PercentWidget
       }

    class Media:
        js = ('js/device-form.js',)

    def clean_payment_processor(self):
        payment_processing = self.cleaned_data['payment_processing']
        payment_processor = self.cleaned_data['payment_processor']

        if payment_processing in ['partially', 'full'] and not payment_processor:
            raise forms.ValidationError('This field is required.')

        return payment_processor

    def clean_api_key(self):
        payment_processing = self.cleaned_data['payment_processing']
        api_key = self.cleaned_data['api_key']

        if payment_processing in ['partially', 'full'] and not api_key:
            raise forms.ValidationError('This field is required.')

        return api_key

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
    time = forms.TimeField(input_formats=['%I:%M %p'], widget=TimeWidget(format='%I:%M %p'))

    class Meta:
        model = ReconciliationTime
        fields = ['email', 'time']


class EnterAmountForm(forms.Form):
    amount = forms.DecimalField(max_digits=9,
                                decimal_places=2,
                                min_value=Decimal('0.01'))

from decimal import Decimal
from django import forms
from django.core.validators import RegexValidator

from website.models import Device


class PaymentForm(forms.Form):

    device_key = forms.CharField(
        validators=[RegexValidator('^[0-9a-zA-Z]{8,32}$')])
    amount = forms.DecimalField(
        max_digits=9,
        decimal_places=2,
        min_value=Decimal('0.01'))
    bt_mac = forms.CharField(
        required=False,
        validators=[RegexValidator('^[0-9a-fA-F:]{17}$')])
    qr_code = forms.BooleanField(required=False)


class WithdrawalForm(forms.Form):

    device = forms.CharField()
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'))

    def clean_device(self):
        try:
            return Device.objects.get(key=self.cleaned_data['device'])
        except Device.DoesNotExist:
            raise forms.ValidationError('Invalid device key')

    @property
    def error_message(self):
        for field, errors in self.errors.items():
            return '{0} - {1}'.format(field, errors[0]).capitalize()

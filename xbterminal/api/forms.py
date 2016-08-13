from decimal import Decimal
from django import forms
from django.core.validators import RegexValidator


class PaymentForm(forms.Form):

    device_key = forms.CharField(
        validators=[RegexValidator('^[0-9a-zA-Z]{8,64}$')])
    amount = forms.DecimalField(
        max_digits=9,
        decimal_places=2,
        min_value=Decimal('0.01'))
    bt_mac = forms.CharField(
        required=False,
        validators=[RegexValidator('^[0-9a-fA-F:]{17}$')])
    qr_code = forms.BooleanField(required=False)

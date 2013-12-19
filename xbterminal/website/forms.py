from django import forms
from django.contrib.auth.forms import AuthenticationForm as DjangoAuthenticationForm

from website.models import MerchantAccount


class ContactForm(forms.Form):
    """
    Simple contact form
    """
    email = forms.EmailField()
    name = forms.CharField()
    company_name = forms.CharField(required=False)
    message = forms.CharField(widget=forms.Textarea)


class MerchantRegistrationForm(forms.ModelForm):
    class Meta:
        model = MerchantAccount
        exclude = ['user']


class AuthenticationForm(DjangoAuthenticationForm):
    def __init__(self, request=None, *args, **kwargs):
        super(AuthenticationForm, self).__init__(*args, **kwargs)

        self.fields['username'].label = 'Email'

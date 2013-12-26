from django import forms
from django.contrib.auth.forms import AuthenticationForm as DjangoAuthenticationForm

from website.models import MerchantAccount, Device


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
    class Meta:
        model = Device
        exclude = ('merchant',)

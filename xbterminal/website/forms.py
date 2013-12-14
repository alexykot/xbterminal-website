from django import forms
from website.models import Contact, MerchantAccount

class ContactForm(forms.Form):
  """
  Simple contact form
  """
  email = forms.EmailField()
  name = forms.CharField()
  company_name = forms.CharField()
  message = forms.CharField(widget=forms.Textarea)

"""
class MerchantAccountForm(forms.ModelForm):
  class Meta:
    model = MerchantAccount
    exclude = ['add_date','is_enabled']
"""

class MerchantRegistrationForm(forms.ModelForm):
  class Meta:
    model = MerchantAccount
    exclude = ['user']
  """
  company_name = forms.CharField()
  business_address = forms.CharField()
  business_address1 = forms.CharField()
  business_address2 = forms.CharField()
  town = forms.CharField()
  county = forms.CharField()
  post_code = forms.CharField()
  contact_name = forms.CharField()
  contact_phone = forms.CharField()
  contact_email = forms.EmailField()
  """

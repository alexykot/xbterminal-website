from django import forms
from website.models import Contact, MerchantAccount

class ContactForm(forms.ModelForm):
  """
  Simple contact form
  """
  class Meta:
    model = Contact
    fields = ['email','message']

class MerchantAccountForm(forms.ModelForm):
  """
  Merchant Account register form
  """
  class Meta:
    model = MerchantAccount
    exclude = ['add_date','is_enabled']

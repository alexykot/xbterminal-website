from django import forms
from website.models import Contact

class ContactForm(forms.ModelForm):
  """
  Simple contact form
  """
  class Meta:
    model = Contact
    fields = ['email','message']

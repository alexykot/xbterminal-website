import sys
from django.shortcuts import render
from django.http import HttpResponseRedirect
from website.models import MerchantAccount
from website.forms import ContactForm

def contact(request):
  if request.method == 'POST':
    form = ContactForm(request.POST)
    if form.is_valid():
      form.save()
      return HttpResponseRedirect('/')
  else:
    form = ContactForm()
  return render(request,'website/contact.html',{'form': form})

def landing(request):
  return render(request,'website/landing.html',{})

def landing_faq(request):
  return render(request,'website/faq.html',{})

def contact_form_save(request):
  # TODO: switch to model-form
  return render(request,'website/index.html',{})

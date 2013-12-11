from django.shortcuts import render
from website.models import MerchantAccount

def index(request):
  return render(request,'website/index.html',{})

def landing(request):
  return render(request,'website/landing.html',{})

def landing_faq(request):
  return render(request,'website/faq.html',{})

def contact_form_save(request):
  # TODO: switch to model-form
  return render(request,'website/index.html',{})

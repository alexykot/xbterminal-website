import sys
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate
from website.models import MerchantAccount
from website.forms import *

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

def merchant_login(request):
  if request.method == 'POST':
    login_form = AuthenticationForm(request,data=request.POST)
    if login_form.is_valid():
      user = authenticate(
        username=login_form.data['username'],
        password=login_form.data['password'])
      if user is not None:
        if user.is_active:
          login(request,user)
          return HttpResponseRedirect('/')
        else:
          return HttpResponseRedirect('/')
      else:
        return HttpResponseRedirect('/')
  else:
    return render(request,'website/login.html',{'form': AuthenticationForm()})

def merchant(request):
  if request.method == 'POST':
    form = MerchantAccountForm(request.POST)
    if form.is_valid():
      form.save()
      return HttpResponseRedirect('/')
  else:
    form = MerchantAccountForm()
  return render(request,'website/merchant.html',{'form': form})

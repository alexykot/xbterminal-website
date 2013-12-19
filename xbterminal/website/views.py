import sys
import json

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, HttpResponse

from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from website.models import MerchantAccount
from website.forms import ContactForm, MerchantRegistrationForm


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            mail_text = render_to_string('website/email/contact.txt', form.cleaned_data)

            send_mail(
                "message from xbterminal.com",
                mail_text,
                "webusnix@gmail.com",
                settings.CONTACT_EMAIL_RECIPIENTS,
                fail_silently=False
            )
            return HttpResponse(json.dumps({'result': 'ok'}), content_type='application/json')
        else:
            errors = {
                'result': 'error',
                'errors': form.errors
            }
            return HttpResponse(json.dumps(errors), content_type='application/json')
    else:
        form = ContactForm()
    return render(request, 'website/contact.html', {'form': form})


def landing(request):
    return render(request, 'website/landing.html', {})


def landing_faq(request):
    return render(request, 'website/faq.html', {})


def merchant_login(request):
    if request.method == 'POST':
        login_form = AuthenticationForm(request, data=request.POST)
        if login_form.is_valid():
            user = authenticate(
                username=login_form.data['username'],
                password=login_form.data['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect(merchant_cabinet)
                else:
                    return HttpResponseRedirect('/')
            else:
                return HttpResponseRedirect('/')
    else:
        return render(request, 'website/login.html', {'form': AuthenticationForm()})


def merchant(request):
    form = None
    if request.method == 'POST':
        form = MerchantRegistrationForm(request.POST)
        if form.is_valid():
            pwd = User.objects.make_random_password()
            user = User.objects.create_user(form.data['company_name'], form.data['contact_email'], pwd)
            user.save()
            mail_text = ""
            mail_text += "Thank you to register on xbterminal.com" + '\n'
            mail_text += "You can logon to the site with your company name and password" + '\n'
            mail_text += "Your company name: " + form.data['company_name'] + '\n'
            mail_text += "Your current password: " + pwd + '\n'
            send_mail(
                "registration on xbterminal.com",
                mail_text,
                "webusnix@gmail.com",
                [form.data['contact_email']],
                fail_silently=False)
            form.save()
            merch = MerchantAccount.objects.get(company_name=form.data['company_name'])
            merch.user = user
            merch.save()

            errors = {}
            errors['msg'] = 'ok'
            return HttpResponse(json.dumps(errors), content_type='application/json')
        else:
            errors = form.errors
            errors['msg'] = 'error'
            return HttpResponse(json.dumps(errors), content_type='application/json')
    else:
        form = MerchantRegistrationForm()
    return render(request, 'website/merchant.html', {'form': form})


@login_required(login_url='/login')
def merchant_cabinet(request):
    return render(request, 'website/merchant_cabinet.html', {})

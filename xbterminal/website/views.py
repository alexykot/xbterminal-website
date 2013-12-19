import sys
import json

from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, HttpResponse

from django.contrib.auth import login, authenticate, get_user_model
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
            to_response = {
                'result': 'error',
                'errors': form.errors
            }
            return HttpResponse(json.dumps(to_response), content_type='application/json')
    else:
        form = ContactForm()
    return render(request, 'website/contact.html', {'form': form})


def landing(request):
    return render(request, 'website/landing.html', {})


def landing_faq(request):
    return render(request, 'website/faq.html', {})


def merchant(request):
    if request.method == 'POST':
        form = MerchantRegistrationForm(request.POST)
        if form.is_valid():
            UserModel = get_user_model()
            password = UserModel.objects.make_random_password()
            email = form.data['contact_email']
            user = UserModel.objects.create_user(email, email, password)

            merchant = form.save(commit=False)
            merchant.user = user
            merchant.save()

            mail_text = render_to_string('website/email/registration.txt',
                                         {'email': email, 'password': password})
            send_mail(
                "registration on xbterminal.com",
                mail_text,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False
            )

            to_response = {
                'result': 'ok'
            }
        else:
            to_response = {
                'result': 'error',
                'errors': form.errors
            }
        return HttpResponse(json.dumps(to_response), content_type='application/json')
    else:
        form = MerchantRegistrationForm()

    return render(request, 'website/merchant.html', {'form': form})


@login_required
def merchant_cabinet(request):
    return render(request, 'website/merchant_cabinet.html', {})

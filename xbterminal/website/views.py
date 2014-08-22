import json
import datetime

from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.views.generic import View
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.utils.decorators import method_decorator
from django.core.urlresolvers import resolve, reverse, reverse_lazy
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Sum
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import ugettext as _

from payment.blockchain import construct_bitcoin_uri

from website.models import Device, ReconciliationTime
from website.forms import (
    ProfileForm,
    DeviceForm,
    SendDailyReconciliationForm,
    SendReconciliationForm)

from website import forms, models, utils


class LandingView(TemplateResponseMixin, View):
    """
    Landing page
    """
    template_name = "website/landing.html"

    def get(self, *args, **kwargs):
        return self.render_to_response({})


class ContactView(TemplateResponseMixin, View):
    """
    Contact form
    """
    template_name = "website/contact.html"

    def get(self, *args, **kwargs):
        form = forms.ContactForm()
        return self.render_to_response({'form': form})

    def post(self, *args, **kwargs):
        form = forms.ContactForm(self.request.POST)
        if form.is_valid():
            mail_text = render_to_string(
                'website/email/contact.txt',
                form.cleaned_data)
            send_mail(
                _("Message from xbterminal.io"),
                mail_text,
                settings.DEFAULT_FROM_EMAIL,
                settings.CONTACT_EMAIL_RECIPIENTS,
                fail_silently=False)
            return self.render_to_response({})
        else:
            return self.render_to_response({'form': form})


class PrivacyPolicyView(TemplateResponseMixin, View):
    """
    Privacy policy page
    """
    template_name = "website/privacy.html"

    def get(self, *args, **kwargs):
        return self.render_to_response({})


class TermsConditionsView(TemplateResponseMixin, View):
    """
    Terms & Conditions page
    """
    template_name = "website/tc.html"

    def get(self, *args, **kwargs):
        return self.render_to_response({})


class TeamView(TemplateResponseMixin, View):
    """
    Team page
    """
    template_name = "website/team.html"

    def get(self, *args, **kwargs):
        return self.render_to_response({})


class LoginView(TemplateResponseMixin, View):
    """
    Login page
    """
    template_name = "cabinet/login.html"

    def get(self, *args, **kwargs):
        if hasattr(self.request.user, 'merchant'):
            return redirect(reverse('website:devices'))
        return self.render_to_response({'form': AuthenticationForm})

    def post(self, *args, **kwargs):
        form = AuthenticationForm(self.request, data=self.request.POST)
        if form.is_valid():
            login(self.request, form.get_user())
            return redirect(reverse('website:devices'))
        return self.render_to_response({'form': form})


class LogoutView(View):
    """
    Logout
    """
    def get(self, *args, **kwargs):
        logout(self.request)
        return redirect(reverse('website:landing'))


class RegistrationView(TemplateResponseMixin, View):
    """
    Registration page
    """
    template_name = "cabinet/registration.html"

    def get(self, *args, **kwargs):
        regtype = self.request.GET.get('regtype', 'default')
        if hasattr(self.request.user, 'merchant'):
            return redirect(reverse('website:devices'))
        context = {
            'form': forms.MerchantRegistrationForm(initial={'regtype': regtype}),
            'order_form': forms.TerminalOrderForm(initial={'quantity': 1}),
        }
        return self.render_to_response(context)

    def post(self, *args, **kwags):
        form = forms.MerchantRegistrationForm(self.request.POST)
        if not form.is_valid():
            response = {
                'result': 'error',
                'errors': form.errors,
            }
            return HttpResponse(json.dumps(response),
                                content_type='application/json')
        regtype = form.cleaned_data['regtype']
        if regtype == 'terminal':
            order_form = forms.TerminalOrderForm(self.request.POST)
            if not order_form.is_valid():
                response = {
                    'result': 'error',
                    'errors': order_form.errors,
                }
                return HttpResponse(json.dumps(response),
                                    content_type='application/json')
        merchant = form.save()
        if regtype == 'default':
            utils.send_registration_info(merchant)
            response = {
                'result': 'ok',
                'next': reverse('website:devices'),
            }
        elif regtype == 'terminal':
            order = order_form.save(merchant)
            # Create devices
            for idx in range(order.quantity):
                device = models.Device(
                    device_type='hardware',
                    status='preordered',
                    name='Terminal #{0}'.format(idx + 1),
                    merchant=merchant)
                device.save()
            utils.send_registration_info(merchant, order)
            response = {
                'result': 'ok',
                'next': reverse('website:order', kwargs={'pk': order.pk}),
            }
        elif regtype == 'web':
            device = models.Device(
                device_type='web',
                status='active',
                name='Web POS #1',
                merchant=merchant)
            device.save()
            utils.send_registration_info(merchant)
            response = {
                'result': 'ok',
                'next': reverse('website:devices'),
            }
        login(self.request, merchant.user)
        return HttpResponse(json.dumps(response),
                            content_type='application/json')


class RegValidationView(View):
    """
    Helper view for server-side validation
    """
    def get(self, *args, **kwargs):
        email = self.request.GET.get('email')
        try:
            models.MerchantAccount.objects.get(contact_email=email)
        except models.MerchantAccount.DoesNotExist:
            response = {'email': True}
        else:
            response = {'email': False}
        return HttpResponse(json.dumps(response),
                            content_type='application/json')


class CabinetView(ContextMixin, View):
    """
    Base class for cabinet views
    """

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'merchant'):
            raise Http404
        return super(CabinetView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CabinetView, self).get_context_data(**kwargs)
        context['cabinet_page'] = resolve(self.request.path_info).url_name
        return context


class OrderPaymentView(TemplateResponseMixin, CabinetView):
    """
    Terminal order page
    """
    template_name = "cabinet/order.html"

    def get(self, *args, **kwargs):
        order = get_object_or_404(models.Order,
                                  pk=self.kwargs.get('pk'),
                                  merchant=self.request.user.merchant)
        if order.payment_method == 'bitcoin':
            context = self.get_context_data(**kwargs)
            context['order'] = order
            context['bitcoin_uri'] = construct_bitcoin_uri(
                context['order'].instantfiat_address,
                context['order'].instantfiat_btc_total_amount,
                "xbterminal.io")
            context['check_url'] = reverse('website:order_check',
                                           kwargs={'pk': order.pk})
            return self.render_to_response(context)
        elif order.payment_method == 'wire':
            utils.send_invoice(order)
            return redirect(reverse('website:devices'))


class OrderCheckView(CabinetView):
    """
    Check payment
    """
    def get(self, *args, **kwargs):
        order = get_object_or_404(models.Order,
                                  pk=self.kwargs.get('pk'),
                                  merchant=self.request.user.merchant)
        if order.payment_status == 'unpaid':
            data = {'paid': 0}
        else:
            data = {'paid': 1, 'next': reverse('website:devices')}
        return HttpResponse(json.dumps(data),
                            content_type='application/json')


class DeviceList(TemplateResponseMixin, CabinetView):
    """
    Device list page
    """
    template_name = "cabinet/device_list.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['devices'] = self.request.user.merchant.device_set.all()
        return self.render_to_response(context)


class CreateDeviceView(TemplateResponseMixin, CabinetView):
    """
    Add terminal page
    """
    template_name = "cabinet/device_form.html"

    def get(self, *args, **kwargs):
        device_types = dict(models.Device.DEVICE_TYPES)
        device_type = self.request.GET.get('device_type', 'hardware')
        if device_type not in device_types:
            return HttpResponseBadRequest('')
        count = self.request.user.merchant.device_set.count()
        context = self.get_context_data(**kwargs)
        context['form'] = forms.DeviceForm(initial={
            'device_type': device_type,
            'name': u'{0} #{1}'.format(device_types[device_type], count + 1),
        })
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        form = forms.DeviceForm(self.request.POST)
        if form.is_valid():
            device = form.save(commit=False)
            device.merchant = self.request.user.merchant
            device.payment_processor = 'GoCoin'
            device.save()
            return redirect(reverse('website:device',
                                    kwargs={'device_key': device.key}))
        else:
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)


class DeviceMixin(ContextMixin):
    """
    Adds device to the context
    """

    def get_context_data(self, **kwargs):
        context = super(DeviceMixin, self).get_context_data(**kwargs)
        try:
            context['device'] = self.request.user.merchant.device_set.get(
                key=self.kwargs.get('device_key'))
        except Device.DoesNotExist:
            raise Http404
        return context


class UpdateDeviceView(DeviceMixin, TemplateResponseMixin, CabinetView):
    """
    Update device
    """
    template_name = "cabinet/device_form.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.DeviceForm(instance=context['device'])
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.DeviceForm(self.request.POST,
                                instance=context['device'])
        if form.is_valid():
            device = form.save()
            return redirect(reverse('website:device',
                                    kwargs={'device_key': device.key}))
        else:
            context['form'] = form
            return self.render_to_response(context)


class UpdateProfileView(TemplateResponseMixin, CabinetView):
    """
    Update profile
    """
    template_name = "cabinet/profile_form.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.ProfileForm(instance=self.request.user.merchant)
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.ProfileForm(self.request.POST,
                                 instance=self.request.user.merchant)
        if form.is_valid():
            device = form.save()
            return redirect(reverse('website:profile'))
        else:
            context['form'] = form
            return self.render_to_response(context)


class ReconciliationView(DeviceMixin, TemplateResponseMixin, CabinetView):
    """
    Reconciliation page
    """
    template_name = "cabinet/reconciliation.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.SendDailyReconciliationForm()
        context['daily_transaction_info'] = context['device'].\
            transaction_set.\
            extra({'date': "date(time)"}).\
            values('date', 'fiat_currency').\
            annotate(
                count=Count('id'),
                btc_amount=Sum('btc_amount'),
                fiat_amount=Sum('fiat_amount'),
                instantfiat_fiat_amount=Sum('instantfiat_fiat_amount')).\
            order_by('-date')
        context['send_form'] = forms.SendReconciliationForm(
            initial={'email': self.request.user.merchant.contact_email})
        return self.render_to_response(context)


class ReconciliationTimeView(DeviceMixin, CabinetView):
    """
    Edit reconciliation schedule
    """
    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        # Add time
        form = forms.SendDailyReconciliationForm(self.request.POST)
        if form.is_valid():
            rectime = form.save(commit=False)
            context['device'].rectime_set.add(rectime)
            return redirect('website:reconciliation',
                            context['device'].key)
        else:
            return HttpResponse('')

    def delete(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        # Remove time
        try:
            context['device'].rectime_set.get(
                pk=self.kwargs.get('pk')).delete()
        except models.ReconciliationTime.DoesNotExist:
            raise Http404
        return HttpResponse('')


class TransactionsView(DeviceMixin, CabinetView):
    """
    Download transactions as csv file
    """

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        if year and month and day:
            try:
                date = datetime.date(int(year), int(month), int(day))
            except ValueError:
                raise Http404
            transactions = context['device'].get_transactions_by_date(date)
            content_disposition = 'attachment; filename="{0}"'.format(
                utils.get_transactions_filename(context['device'], date))
        else:
            transactions = context['device'].transaction_set.all()
            content_disposition = 'attachment; filename="{0}"'.format(
                utils.get_transactions_filename(context['device']))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = content_disposition
        utils.get_transaction_csv(transactions, response)
        return response


class ReceiptsView(DeviceMixin, CabinetView):
    """
    Download receipts
    """
    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        if year and month and day:
            try:
                date = datetime.date(int(year), int(month), int(day))
            except ValueError:
                raise Http404
            transactions = context['device'].get_transactions_by_date(date)
            content_disposition = 'attachment; filename="{0}"'.format(
                utils.get_receipts_filename(context['device'], date))
        else:
            transactions = context['device'].transaction_set.all()
            content_disposition = 'attachment; filename="{0}"'.format(
                utils.get_receipts_filename(context['device']))
        response = HttpResponse(content_type='application/x-zip-compressed')
        response['Content-Disposition'] = content_disposition
        utils.get_transaction_pdf_archive(transactions, response)
        return response


class SendAllToEmailView(DeviceMixin, CabinetView):
    """
    Send transactions and receipts to email
    """
    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = SendReconciliationForm(self.request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            date = form.cleaned_data['date']
            # Calculate datetime range
            now = timezone.localtime(timezone.now())
            rec_range_beg = timezone.make_aware(
                datetime.datetime.combine(date, datetime.time.min),
                timezone.get_current_timezone())
            if date < now.date():
                rec_range_end = timezone.make_aware(
                    datetime.datetime.combine(date, datetime.time.max),
                    timezone.get_current_timezone())
            else:
                rec_range_end = now
            utils.send_reconciliation(
                email, context['device'],
                (rec_range_beg, rec_range_end))
            messages.success(self.request,
                             _('Email has been sent successfully.'))
        else:
            messages.error(self.request,
                           _('Error: Invalid email. Please, try again.'))
        return redirect('website:reconciliation', context['device'].key)


class SubscribeNewsView(View):
    """
    Subscribe to newsletters (Ajax)
    """
    def post(self, *args, **kwargs):
        form = forms.SubscribeForm(self.request.POST)
        if form.is_valid():
            subscriber_email = form.cleaned_data['email']
            email1 = utils.create_html_message(
                _("XBTerminal newsletter confirmation"),
                "website/email/subscription.html",
                {},
                settings.DEFAULT_FROM_EMAIL,
                [subscriber_email])
            email1.send(fail_silently=False)
            email2 = utils.create_html_message(
                _("Subscription to newsletters"),
                "website/email/subscription.html",
                {'subscriber_email': subscriber_email},
                settings.DEFAULT_FROM_EMAIL,
                settings.CONTACT_EMAIL_RECIPIENTS)
            email2.send(fail_silently=False)
            response = {}
        else:
            response = {'errors': form.errors}
        return HttpResponse(json.dumps(response),
                            content_type='application/json')


class PaymentView(TemplateResponseMixin, View):
    """
    Online POS (public view)
    """

    template_name = "payment/payment.html"

    def get(self, *args, **kwargs):
        device = get_object_or_404(
            models.Device, key=self.kwargs.get('device_key'))
        response = self.render_to_response({'device': device})
        response['X-Frame-Options'] = 'ALLOW-FROM vendhq.com'
        return response

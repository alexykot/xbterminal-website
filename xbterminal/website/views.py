from decimal import Decimal
import json
import datetime
import logging

from django.shortcuts import render, redirect
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.views.generic import UpdateView, ListView, View, TemplateView
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse, reverse_lazy
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Sum
from django.contrib import messages
from django.utils import timezone

import constance.config

from website.models import Device, ReconciliationTime, PaymentRequest, Transaction
from website.forms import (
    ContactForm,
    MerchantRegistrationForm,
    ProfileForm,
    DeviceForm,
    SendDailyReconciliationForm,
    SendReconciliationForm,
    SubscribeForm,
    EnterAmountForm)
    
from website.utils import (
    get_transaction_csv,
    get_transaction_pdf_archive,
    send_reconciliation,
    generate_qr_code)

import payment.average
import payment.blockchain
import payment.protocol

logger = logging.getLogger(__name__)


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            mail_text = render_to_string('website/email/contact.txt', form.cleaned_data)

            send_mail(
                "message from xbterminal.com",
                mail_text,
                settings.DEFAULT_FROM_EMAIL,
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

def profiles(request):
    return render(request, 'website/profiles.html', {})


class SubscribeNewsView(View):
    """
    Subscribe to newsletters (Ajax)
    """
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        form = SubscribeForm(request.POST)
        if form.is_valid():
            subscriber_email = form.data['email']
            text = render_to_string(
                "website/email/subscription.txt",
                {'subscriber_email': subscriber_email})
            send_mail(
                "Subscription to newsletters",
                text,
                settings.DEFAULT_FROM_EMAIL,
                settings.CONTACT_EMAIL_RECIPIENTS,
                fail_silently=False)
            return HttpResponse("")
        else:
            raise Http404


@xframe_options_exempt
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


class ProfileView(UpdateView):
    form_class = ProfileForm
    template_name = 'cabinet/profile_form.html'
    success_url = reverse_lazy('website:profile')

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ProfileView, self).dispatch(*args, **kwargs)

    def get_object(self):
        user = self.request.user
        if not hasattr(user, 'merchant'):
            raise Http404
        return user.merchant


def get_device(merchant, number):
    if number is not None:
        try:
            number = int(number) - 1
            device = merchant.device_set.all()[number]
        except IndexError:
            raise Http404
    else:
        device = None

    return device


class DeviceView(UpdateView):
    form_class = DeviceForm
    template_name = 'cabinet/device_form.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(DeviceView, self).dispatch(*args, **kwargs)

    def get_object(self):
        user = self.request.user
        if not hasattr(user, 'merchant'):
            raise Http404

        number = self.kwargs.get('number')
        device = get_device(user.merchant, number)

        return device

    def form_valid(self, form):
        device = form.save(commit=False)
        device.merchant = self.request.user.merchant
        device.save()
        self.object = device
        return super(DeviceView, self).form_valid(form)

    def get_success_url(self):
        return reverse('website:devices')

    def get_context_data(self, **kwargs):
        kwargs['current_device'] = self.object
        return super(DeviceView, self).get_context_data(**kwargs)


class DeviceList(ListView):
    model = Device
    template_name = 'cabinet/device_list.html'
    context_object_name = 'devices'

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'merchant'):
            raise Http404

        return self.request.user.merchant.device_set.all()


def reconciliation(request, number):
    user = request.user
    if not hasattr(user, 'merchant'):
        raise Http404

    device = get_device(user.merchant, number)

    daily_transaction_info = device.transaction_set.extra({'date': "date(time)"})\
                                                   .values('date', 'fiat_currency')\
                                                   .annotate(count=Count('id'),
                                                             btc_amount=Sum('btc_amount'),
                                                             fiat_amount=Sum('fiat_amount'),
                                                             instantfiat_fiat_amount=Sum('instantfiat_fiat_amount'))

    return render(request, 'cabinet/reconciliation.html', {
        'form': SendDailyReconciliationForm(),
        'device': device,
        'daily_transaction_info': daily_transaction_info,
        'number': number,
        'send_form': SendReconciliationForm(initial={'email': user.merchant.contact_email}),
        'reconciliation_schedule': device.rectime_set.all(),
    })


@require_http_methods(['POST', 'DELETE'])
def reconciliation_time(request, number, pk):
    user = request.user
    if not hasattr(user, 'merchant'):
        raise Http404
    device = get_device(user.merchant, number)

    if request.method == 'POST':
        # Add time
        form = SendDailyReconciliationForm(request.POST)
        if form.is_valid():
            rectime = form.save(commit=False)
            device.rectime_set.add(rectime)
            return redirect('website:reconciliation', number=number)
    else:
        # Remove time
        try:
            device.rectime_set.get(pk=pk).delete()
        except ReconciliationTime.DoesNotExist:
            raise Http404
        return HttpResponse('')


def transactions(request, number, year=None, month=None, day=None):
    user = request.user
    if not hasattr(user, 'merchant'):
        raise Http404

    device = get_device(user.merchant, number)

    if year and month and day:
        try:
            date = datetime.date(int(year), int(month), int(day))
        except ValueError:
            raise Http404

        transactions = device.get_transactions_by_date(date)
        cd_template = 'attachment; filename="%s device transactions %s.csv"'
        content_disposition = cd_template % (device.name, date.strftime('%d %b %Y'))
    else:
        transactions = device.transaction_set.all()
        cd_template = 'attachment; filename="%s device transactions.csv"'
        content_disposition = cd_template % device.name

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = content_disposition

    get_transaction_csv(transactions, response)
    return response


def receipts(request, number, year=None, month=None, day=None):
    user = request.user
    if not hasattr(user, 'merchant'):
        raise Http404

    device = get_device(user.merchant, number)

    if year and month and day:
        try:
            date = datetime.date(int(year), int(month), int(day))
        except ValueError:
            raise Http404

        transactions = device.get_transactions_by_date(date)
        cd_template = 'attachment; filename="%s device receipts %s.zip"'
        content_disposition = cd_template % (device.name, date.strftime('%d %b %Y'))
    else:
        transactions = device.transaction_set.all()
        cd_template = 'attachment; filename="%s device receipts.zip"'
        content_disposition = cd_template % device.name

    response = HttpResponse(content_type='application/x-zip-compressed')

    response['Content-Disposition'] = content_disposition

    get_transaction_pdf_archive(transactions, response)
    return response


def send_all_to_email(request, number):
    user = request.user
    if not hasattr(user, 'merchant'):
        raise Http404

    device = get_device(user.merchant, number)

    if request.method != 'POST':
        raise Http404

    form = SendReconciliationForm(request.POST)

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
        send_reconciliation(
            email,
            device,
            (rec_range_beg, rec_range_end))
        messages.success(request, 'Email has been sent successfully.')
    else:
        messages.error(request, 'Error: Invalid email. Please, try again.')

    return redirect('website:reconciliation', number)


class PaymentView(TemplateView):
    """
    Base class
    """

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'merchant'):
            raise Http404
        return super(PaymentView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PaymentView, self).get_context_data(**kwargs)
        context['number'] = self.kwargs.get('number')
        context['merchant'] = self.request.user.merchant
        context['device'] = get_device(context['merchant'], context['number'])
        return context


class EnterAmountView(PaymentView):
    """
    Payment - first step, enter amount
    """

    template_name = "payment/enter_amount.html"


class PaymentInitView(PaymentView):
    """
    Payment - second step, prepare payment and show payment uri
    """

    http_method_names = ['post']
    template_name = "payment/payment_init.html"

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        device = context['device']
        form = EnterAmountForm(self.request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()
        # Prepare payment request
        payment_request = payment.prepare_payment(device,
                                                  form.cleaned_data['amount'])
        payment_request.save()
        payment_request_url = self.request.build_absolute_uri(reverse(
            'website:payment_request',
            kwargs={'uid': payment_request.uid}))
        # Create bitcoin uri and QR code
        payment_uri = payment.blockchain.construct_bitcoin_uri(
            payment_request.local_address,
            payment_request.btc_amount,
            payment_request_url)
        qr_code_src = generate_qr_code(payment_uri, size=4)
        # Update context
        context['fiat_amount'] = payment_request.fiat_amount
        context['mbtc_amount'] = payment_request.btc_amount / Decimal('0.001')
        context['exchange_rate'] = payment_request.effective_exchange_rate * Decimal('0.001')
        context['request_uid'] = payment_request.uid
        context['payment_uri'] = payment_uri
        context['qr_code_src'] = qr_code_src
        return self.render_to_response(context)


class PaymentRequestView(View):
    """
    Payment - third step, send PaymentRequest
    """

    def get(self, *args, **kwargs):
        try:
            payment_request = PaymentRequest.objects.get(uid=self.kwargs.get('uid'))
        except PaymentRequest.DoesNotExist:
            raise Http404
        if payment_request.expires < timezone.now():
            raise Http404
        payment_response_url = self.request.build_absolute_uri(reverse(
            'website:payment_response',
            kwargs={'uid': payment_request.uid}))
        message = payment.protocol.create_payment_request(
            payment_request.device.bitcoin_network,
            [(payment_request.local_address, payment_request.btc_amount)],
            payment_request.created,
            payment_request.expires,
            payment_response_url,
            "xbterminal.com")
        response = HttpResponse(message.SerializeToString(),
                                content_type='application/bitcoin-paymentrequest')
        response['Content-Transfer-Encoding'] = 'binary'
        return response


class PaymentResponseView(View):
    """
    Payment - fourth step, accept and forward payment
    """

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(PaymentResponseView, self).dispatch(*args, **kwargs)

    def post(self, *args, **kwargs):
        content_type = self.request.META.get('CONTENT_TYPE')
        if content_type != 'application/bitcoin-payment':
            return HttpResponseBadRequest()
        message = self.request.body
        if len(message) > 50000:
            # Payment messages larger than 50,000 bytes should be rejected by server
            return HttpResponseBadRequest()
        try:
            payment_request = PaymentRequest.objects.get(uid=self.kwargs.get('uid'))
        except PaymentRequest.DoesNotExist:
            raise Http404
        transactions, payment_response = payment.protocol.parse_payment(message)
        # Validate transactions
        bc = payment.blockchain.BlockChain(payment_request.device.bitcoin_network)
        if len(transactions) != 1:
            return HttpResponseBadRequest()
        incoming_tx = transactions[0]
        if not bc.is_valid_transaction(incoming_tx):
            return HttpResponseBadRequest()
        # Create transaction
        transaction = payment.create_transaction(payment_request, incoming_tx)
        transaction.save()
        payment_request.transaction = transaction
        payment_request.save()
        # Send PaymentACK
        payment_ack = payment.protocol.create_payment_ack(payment_response)
        response = HttpResponse(payment_ack.SerializeToString(),
                                content_type='application/bitcoin-paymentack')
        response['Content-Transfer-Encoding'] = 'binary'
        return response


class PaymentCheckView(View):

    def get(self, *args, **kwargs):
        try:
            payment_request = PaymentRequest.objects.get(uid=self.kwargs.get('uid'))
        except PaymentRequest.DoesNotExist:
            raise Http404
        data = {'paid': int(payment_request.transaction is not None)}
        response = HttpResponse(json.dumps(data),
                                content_type='application/json')
        return response


class PaymentSuccessView(PaymentView):
    """
    Payment - last step, show receipt
    """

    template_name = "payment/payment_success.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        # Get payment request
        try:
            payment_request = PaymentRequest.objects.get(uid=self.request.GET.get('request_uid'))
        except PaymentRequest.DoesNotExist:
            raise Http404
        receipt_url = self.request.build_absolute_uri(reverse(
            'api:transaction_pdf',
            kwargs={'key': payment_request.transaction.receipt_key}))
        qr_code_src = generate_qr_code(receipt_url, size=3)
        # Update context
        context['receipt_url'] = receipt_url
        context['qr_code_src'] = qr_code_src
        return self.render_to_response(context)

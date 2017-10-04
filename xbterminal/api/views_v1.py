from decimal import Decimal
import json
import logging

from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.utils import timezone
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view
from rest_framework.response import Response
from oauth2_provider.views.generic import ProtectedResourceView

from website.models import Device
from website.forms import SimpleMerchantRegistrationForm
from website.utils.qr import generate_qr_code
from website.utils.email import send_registration_info

from api.forms import PaymentForm
from api.utils.pdf import generate_pdf
from api.utils.urls import construct_absolute_url

from transactions.exceptions import TransactionError
from transactions.models import Deposit
from transactions.deposits import prepare_deposit, handle_bip70_payment
from transactions.services.bitcoind import construct_bitcoin_uri

logger = logging.getLogger(__name__)


class CSRFExemptMixin(object):

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(CSRFExemptMixin, self).dispatch(*args, **kwargs)


class MerchantView(CSRFExemptMixin, View):

    # TODO: remove this view

    def post(self, *args, **kwargs):
        """
        Create merchant
        """
        form = SimpleMerchantRegistrationForm(self.request.POST)
        if form.is_valid():
            merchant = form.save()
            send_registration_info(merchant)
            data = {'merchant_id': merchant.pk}
        else:
            data = {'errors': form.errors}
        response = HttpResponse(json.dumps(data),
                                content_type='application/json')
        return response


class DevicesView(ProtectedResourceView):

    # TODO: remove this view

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(DevicesView, self).dispatch(*args, **kwargs)

    def get(self, *args, **kwargs):
        """
        Device list
        """
        merchant = self.request.resource_owner.merchant
        data = []
        for device in merchant.device_set.all():
            data.append({
                'name': device.name,
                'key': device.key,
                'percent': 0,
                'type': device.device_type,
                'online': device.is_online(),
            })
        response = HttpResponse(json.dumps(data),
                                content_type='application/json')
        return response

    def post(self, *args, **kwargs):
        """
        Create new device
        """
        merchant = self.request.resource_owner.merchant
        name = self.request.POST.get('name')
        if not name:
            return HttpResponseBadRequest()
        device = Device(
            device_type='mobile',
            status='active',
            name=name,
            merchant=merchant)  # Account is not set
        device.save()
        data = {
            'name': device.name,
            'key': device.key,
            'percent': 0,
            'type': device.device_type,
            'online': device.is_online(),
        }
        response = HttpResponse(json.dumps(data),
                                content_type='application/json')
        return response


@api_view(['GET'])
def device(request, key):
    device = get_object_or_404(Device, key=key, status='active')
    response = {
        "MERCHANT_NAME": device.merchant.company_name,
        "MERCHANT_DEVICE_NAME": device.name,
        "MERCHANT_LANGUAGE": device.merchant.language.code,
        "MERCHANT_CURRENCY": device.merchant.currency.name,
        "MERCHANT_CURRENCY_SIGN_POSTFIX": device.merchant.currency.postfix,
        "MERCHANT_CURRENCY_SIGN_PREFIX": device.merchant.currency.prefix,
        "OUTPUT_DEC_FRACTIONAL_SPLIT": device.merchant.language.fractional_split,
        "OUTPUT_DEC_THOUSANDS_SPLIT": device.merchant.language.thousands_split,
        "BITCOIN_NETWORK": device.bitcoin_network,
        "SERIAL_NUMBER": '0000',
    }
    device.last_activity = timezone.now()
    device.save()
    return Response(response)


class ReceiptView(View):
    """
    Download PDF receipt
    """
    def get(self, *args, **kwargs):
        deposit_uid = self.kwargs.get('uid')
        try:
            deposit = Deposit.objects.get(
                uid=deposit_uid, time_notified__isnull=False)
        except Deposit.DoesNotExist:
            raise Http404
        result = generate_pdf(
            'pdf/receipt_deposit.html',
            {'deposit': deposit})
        response = HttpResponse(result.getvalue(),
                                content_type='application/pdf')
        disposition = 'inline; filename="receipt #{0} {1}.pdf"'.format(
            deposit.id,
            deposit.device.merchant.company_name)
        response['Content-Disposition'] = disposition
        return response


class PaymentInitView(View):
    """
    Prepare payment and return payment uri
    """

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(PaymentInitView, self).dispatch(*args, **kwargs)

    def post(self, *args, **kwargs):
        form = PaymentForm(self.request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest(
                json.dumps({'errors': form.errors}),
                content_type='application/json')
        # Prepare payment order
        try:
            device = Device.objects.get(key=form.cleaned_data['device_key'],
                                        status='active')
        except Device.DoesNotExist:
            raise Http404
        try:
            deposit = prepare_deposit(
                device, form.cleaned_data['amount'])
        except TransactionError as error:
            return HttpResponseBadRequest(
                json.dumps({'error': error.message}),
                content_type='application/json')
        # Urls
        payment_request_url = construct_absolute_url(
            'api:short:payment_request',
            kwargs={'uid': deposit.uid})
        payment_check_url = construct_absolute_url(
            'api:payment_check',
            kwargs={'uid': deposit.uid})
        # Prepare json response
        fiat_amount = deposit.amount.quantize(Decimal('0.00'))
        btc_amount = deposit.coin_amount
        exchange_rate = deposit.effective_exchange_rate.\
            quantize(Decimal('0.000000'))
        data = {
            'payment_uid': deposit.uid,
            'fiat_amount': float(fiat_amount),
            'btc_amount': float(btc_amount),
            'exchange_rate': float(exchange_rate),
            'check_url': payment_check_url,
        }
        if form.cleaned_data['bt_mac']:
            # Enable payment via bluetooth
            payment_bluetooth_url = 'bt:{mac}'.\
                format(mac=form.cleaned_data['bt_mac'].replace(':', ''))
            payment_bluetooth_request = deposit.create_payment_request(
                payment_bluetooth_url)
            # Send payment request in response
            data['payment_uri'] = construct_bitcoin_uri(
                deposit.deposit_address.address,
                deposit.coin_amount,
                device.merchant.company_name,
                payment_bluetooth_url,
                payment_request_url)
            data['payment_request'] = payment_bluetooth_request.encode('base64')
        else:
            data['payment_uri'] = construct_bitcoin_uri(
                deposit.deposit_address.address,
                deposit.coin_amount,
                device.merchant.company_name,
                payment_request_url)
        # TODO: append QR code as data URI only when needed
        data['qr_code_src'] = generate_qr_code(data['payment_uri'], size=4)
        response = HttpResponse(json.dumps(data),
                                content_type='application/json')
        return response


class PaymentRequestView(View):
    """
    Send PaymentRequest
    """

    def get(self, *args, **kwargs):
        try:
            deposit = Deposit.objects.get(uid=self.kwargs.get('uid'))
        except Deposit.DoesNotExist:
            raise Http404
        if deposit.status not in ['new', 'underpaid']:
            raise Http404
        payment_response_url = construct_absolute_url(
            'api:payment_response',
            kwargs={'uid': deposit.uid})
        payment_request = deposit.create_payment_request(
            payment_response_url)
        response = HttpResponse(payment_request,
                                content_type='application/bitcoin-paymentrequest')
        response['Content-Transfer-Encoding'] = 'binary'
        return response


class PaymentResponseView(View):
    """
    Accept and forward payment
    """

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(PaymentResponseView, self).dispatch(*args, **kwargs)

    def post(self, *args, **kwargs):
        try:
            deposit = Deposit.objects.get(uid=self.kwargs.get('uid'))
        except Deposit.DoesNotExist:
            raise Http404
        # Check and parse message
        content_type = self.request.META.get('CONTENT_TYPE')
        if content_type != 'application/bitcoin-payment':
            return HttpResponseBadRequest()
        if len(self.request.body) > 50000:
            # Payment messages larger than 50,000 bytes should be rejected by server
            return HttpResponseBadRequest()
        try:
            payment_ack = handle_bip70_payment(deposit, self.request.body)
        except Exception as error:
            logger.exception(error)
            return HttpResponseBadRequest()
        # Send PaymentACK
        response = HttpResponse(payment_ack,
                                content_type='application/bitcoin-paymentack')
        response['Content-Transfer-Encoding'] = 'binary'
        return response


class PaymentCheckView(View):
    """
    Check payment and return receipt
    """

    def get(self, *args, **kwargs):
        try:
            deposit = Deposit.objects.get(uid=self.kwargs.get('uid'))
        except Deposit.DoesNotExist:
            raise Http404
        if deposit.time_broadcasted is not None:
            receipt_url = construct_absolute_url(
                'api:short:receipt',
                kwargs={'uid': deposit.uid})
            qr_code_src = generate_qr_code(receipt_url, size=3)
            data = {
                'paid': 1,
                'receipt_url': receipt_url,
                'qr_code_src': qr_code_src,
            }
            if deposit.time_notified is None:
                deposit.time_notified = timezone.now()
                deposit.save()
        else:
            data = {'paid': 0}
        response = HttpResponse(json.dumps(data),
                                content_type='application/json')
        return response

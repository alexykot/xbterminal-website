from decimal import Decimal
import json
import logging
import os

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.utils import timezone
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view
from rest_framework.response import Response
from constance import config

from website.models import Device, Transaction, Firmware, PaymentOrder, MerchantAccount
from website.forms import EnterAmountForm
from website.utils import generate_qr_code
from api.shortcuts import render_to_pdf

import payment.tasks
import payment.blockchain
import payment.protocol

logger = logging.getLogger(__name__)


class DeviceListView(View):
    """
    Device list
    """
    def get(self, *args, **kwargs):
        merchant = get_object_or_404(MerchantAccount,
                                     pk=self.kwargs.get('pk'))
        data = []
        for device in merchant.device_set.all():
            data.append({
                'name': device.name,
                'key': device.key,
                'percent': float(device.percent),
                'type': device.device_type,
                'is_active': (device.status == 'active'),
            })
        response = HttpResponse(json.dumps(data),
                                content_type='application/json')
        return response


class CreateDeviceView(View):
    """
    Create device
    """
    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(CreateDeviceView, self).dispatch(*args, **kwargs)

    def post(self, *args, **kwargs):
        merchant = get_object_or_404(MerchantAccount,
                                     pk=self.kwargs.get('pk'))
        name = self.request.POST.get('name')
        if not name:
            return HttpResponseBadRequest()
        device = Device(
            device_type='mobile',
            status='active',
            name=name,
            merchant=merchant)
        device.save()
        response = HttpResponse(json.dumps({'key': device.key}),
                                content_type='application/json')
        return response


@api_view(['GET'])
def device(request, key):
    device = get_object_or_404(Device, key=key)
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
        "SERIAL_NUMBER": device.serial_number,
    }
    device.last_activity = timezone.now()
    device.save()
    return Response(response)


def transaction_pdf(request, key):
    transaction = get_object_or_404(Transaction, receipt_key=key)

    response = render_to_pdf('pdf/receipt.html',
                             {'transaction': transaction})
    disposition = 'inline; filename="receipt %s %s.pdf"'.format(
        transaction.id, transaction.device.merchant.company_name)
    response['Content-Disposition'] = disposition
    return response


@api_view(['GET'])
def device_firmware(request, key):
    device = get_object_or_404(Device, key=key)

    response = {
        "current_firmware_version": getattr(device.current_firmware, 'version', None),
        "current_firmware_version_hash": getattr(device.current_firmware, 'hash', None),
        "next_firmware_version": getattr(device.next_firmware, 'version', None),
        "next_firmware_version_hash": getattr(device.next_firmware, 'hash', None),
    }
    return Response(response)


def firmware(request, key, firmware_hash):
    device = get_object_or_404(Device, key=key)
    firmware = get_object_or_404(Firmware, hash=firmware_hash)

    response = HttpResponse(open(firmware.filename, 'rb'),
                            content_type='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(firmware.filename)
    return response


@api_view(['POST'])
def firmware_updated(request, key):
    device = get_object_or_404(Device, key=key)
    firmware_hash = request.DATA.get('firmware_version_hash')
    if not firmware_hash:
        raise Http404
    firmware = get_object_or_404(Firmware, hash=firmware_hash)

    device.current_firmware = firmware
    device.last_firmware_update_date = timezone.now()
    device.next_firmware = None
    device.save()

    return Response()


class PaymentInitView(View):
    """
    Prepare payment and return payment uri
    """

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(PaymentInitView, self).dispatch(*args, **kwargs)

    def post(self, *args, **kwargs):
        form = EnterAmountForm(self.request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()
        # Prepare payment order
        try:
            device = Device.objects.get(key=form.cleaned_data['device_key'])
        except Device.DoesNotExist:
            raise Http404
        try:
            payment_order = payment.tasks.prepare_payment(
                device, form.cleaned_data['amount'])
        except payment.blockchain.NetworkError:
            return HttpResponse(status=500)
        # Urls
        payment_request_url = self.request.build_absolute_uri(reverse(
            'api:payment_request',
            kwargs={'payment_uid': payment_order.uid}))
        payment_response_url = self.request.build_absolute_uri(reverse(
            'api:payment_response',
            kwargs={'payment_uid': payment_order.uid}))
        payment_check_url = self.request.build_absolute_uri(reverse(
            'api:payment_check',
            kwargs={'payment_uid': payment_order.uid}))
        # Create payment request
        payment_order.request = payment.protocol.create_payment_request(
            payment_order.device.bitcoin_network,
            [(payment_order.local_address, payment_order.btc_amount)],
            payment_order.created,
            payment_order.expires,
            payment_response_url,
            device.merchant.company_name)
        payment_order.save()
        # Prepare json response
        fiat_amount = payment_order.fiat_amount.quantize(Decimal('0.00'))
        btc_amount = payment_order.btc_amount
        exchange_rate = payment_order.effective_exchange_rate.\
            quantize(Decimal('0.000000'))
        data = {
            'fiat_amount': float(fiat_amount),
            'btc_amount': float(btc_amount),
            'exchange_rate': float(exchange_rate),
            'check_url': payment_check_url,
        }
        if form.cleaned_data['bt_mac']:
            # Payment with terminal
            payment_bluetooth_url = 'bt:{mac}'.\
                format(mac=form.cleaned_data['bt_mac'].replace(':', ''))
            payment_bluetooth_request = payment.protocol.create_payment_request(
                payment_order.device.bitcoin_network,
                [(payment_order.local_address, payment_order.btc_amount)],
                payment_order.created,
                payment_order.expires,
                payment_bluetooth_url,
                device.merchant.company_name)
            # Append bitcoin uri, payment uid, and payment request
            data['payment_uri'] = payment.blockchain.construct_bitcoin_uri(
                payment_order.local_address,
                payment_order.btc_amount,
                device.merchant.company_name,
                payment_bluetooth_url,
                payment_request_url)
            data['payment_uid'] = payment_order.uid
            data['payment_request'] = payment_bluetooth_request.encode('base64')
        else:
            # Payment via website
            data['payment_uri'] = payment.blockchain.construct_bitcoin_uri(
                payment_order.local_address,
                payment_order.btc_amount,
                device.merchant.company_name,
                payment_request_url)
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
            payment_order = PaymentOrder.objects.get(uid=self.kwargs.get('payment_uid'))
        except PaymentOrder.DoesNotExist:
            raise Http404
        if payment_order.expires < timezone.now():
            raise Http404
        response = HttpResponse(payment_order.request,
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
            payment_order = PaymentOrder.objects.get(uid=self.kwargs.get('payment_uid'))
        except PaymentOrder.DoesNotExist:
            raise Http404
        # Check and parse message
        content_type = self.request.META.get('CONTENT_TYPE')
        if content_type != 'application/bitcoin-payment':
            logger.warning("PaymentResponseView: wrong content type")
            return HttpResponseBadRequest()
        message = self.request.body
        if len(message) > 50000:
            # Payment messages larger than 50,000 bytes should be rejected by server
            logger.warning("PaymentResponseView: message is too large")
            return HttpResponseBadRequest()
        try:
            transactions, payment_ack = payment.protocol.parse_payment(message)
        except Exception as error:
            logger.warning("PaymentResponseView: parser error {0}".\
                format(error.__class__.__name__))
            return HttpResponseBadRequest()
        # Validate payment
        try:
            payment.tasks.validate_payment(payment_order, transactions, broadcast=True)
        except Exception as error:
            logger.warning("PaymentResponseView: validation error {0}".\
                format(error.__class__.__name__))
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
            payment_order = PaymentOrder.objects.get(uid=self.kwargs.get('payment_uid'))
        except PaymentOrder.DoesNotExist:
            raise Http404
        if payment_order.transaction is None:
            data = {'paid': 0}
        else:
            receipt_url = self.request.build_absolute_uri(reverse(
                'api:transaction_pdf',
                kwargs={'key': payment_order.transaction.receipt_key}))
            qr_code_src = generate_qr_code(receipt_url, size=3)
            data = {
                'paid': 1,
                'receipt_url': receipt_url,
                'qr_code_src': qr_code_src,
            }
        response = HttpResponse(json.dumps(data),
                                content_type='application/json')
        return response

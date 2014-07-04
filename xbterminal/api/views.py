from decimal import Decimal
import json
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
from rest_framework.generics import CreateAPIView
from constance import config

from website.models import Device, Transaction, Firmware, PaymentOrder
from website.forms import EnterAmountForm
from website.utils import generate_qr_code
from api.serializers import TransactionSerializer
from api.shotcuts import render_to_pdf

import payment
import payment.blockchain
import payment.protocol


@api_view(['GET'])
def device(request, key):
    device = get_object_or_404(Device, key=key)
    response = {
        "MERCHANT_BITCOIN_ADDRESS": device.bitcoin_address,
        "MERCHANT_CURRENCY": device.currency.name,
        "MERCHANT_CURRENCY_SIGN_POSTFIX": device.currency.postfix,
        "MERCHANT_CURRENCY_SIGN_PREFIX": device.currency.prefix,
        "MERCHANT_DEVICE_NAME": device.name,
        "MERCHANT_INSTANTFIAT_API_KEY": device.api_key,
        "MERCHANT_INSTANTFIAT_EXCHANGE_SERVICE": device.payment_processor,
        "MERCHANT_INSTANTFIAT_SHARE": float(device.percent / 100) if device.percent else 0,
        "MERCHANT_INSTANTFIAT_TRANSACTION_SPEED": "high",
        "MERCHANT_NAME": device.merchant.company_name,
        "MERCHANT_TRANSACTION_DESCRIPTION": "Payment to %s" % device.merchant.company_name,
        "OUR_FEE_BITCOIN_ADDRESS": device.our_fee_override if device.our_fee_override else config.OUR_FEE_BITCOIN_ADDRESS,
        "OUR_FEE_SHARE": config.OUR_FEE_SHARE,
        "OUTPUT_DEC_FRACTIONAL_SPLIT": device.language.fractional_split,
        "OUTPUT_DEC_THOUSANDS_SPLIT": device.language.thousands_split,
        "SERIAL_NUMBER": device.serial_number,
        "BITCOIN_NETWORK": device.bitcoin_network
    }
    return Response(response)


class CreateTransaction(CreateAPIView):
    model = Transaction
    serializer_class = TransactionSerializer


def transaction_pdf(request, key):
    transaction = get_object_or_404(Transaction, receipt_key=key)

    response = render_to_pdf(
        'api/transaction.html', {
            'transaction': transaction,
            'STATIC_ROOT': settings.STATIC_ROOT
        }
    )

    disposition = 'inline; filename="receipt %s %s.pdf"' %\
        (transaction.id, transaction.device.merchant.company_name)
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
        payment_order = payment.prepare_payment(device,
                                                form.cleaned_data['amount'])
        # Urls
        if form.cleaned_data['bt_mac']:
            # Payment with terminal
            payment_request_url = payment_response_url = 'bt:{mac}'.format(
                mac=form.cleaned_data['bt_mac'].replace(':', ''))
        else:
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
            "xbterminal.com")
        payment_order.save()
        # Create bitcoin uri
        payment_uri = payment.blockchain.construct_bitcoin_uri(
            payment_order.local_address,
            payment_order.btc_amount,
            payment_request_url)
        # Return JSON
        fiat_amount = payment_order.fiat_amount.quantize(Decimal('0.00'))
        btc_amount = payment_order.btc_amount
        exchange_rate = payment_order.effective_exchange_rate.\
            quantize(Decimal('0.000000'))
        data = {
            'fiat_amount': float(fiat_amount),
            'btc_amount': float(btc_amount),
            'exchange_rate': float(exchange_rate),
            'payment_uri': payment_uri,
            'qr_code_src': generate_qr_code(payment_uri, size=4),
            'check_url': payment_check_url,
        }
        if form.cleaned_data['bt_mac']:
            # Append payment uid and payment request for terminals
            data['payment_uid'] = payment_order.uid
            data['payment_request'] = payment_order.request.encode('base64')
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
            return HttpResponseBadRequest()
        message = self.request.body
        if len(message) > 50000:
            # Payment messages larger than 50,000 bytes should be rejected by server
            return HttpResponseBadRequest()
        try:
            transactions, payment_ack = payment.protocol.parse_payment(message)
        except Exception:
            return HttpResponseBadRequest()
        # Validate payment
        try:
            payment.validate_payment(payment_order, transactions)
        except Exception as error:
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

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

from website.models import Device, Transaction, Firmware, PaymentRequest
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
        # Prepare payment request
        try:
            device = Device.objects.get(key=form.cleaned_data['device_key'])
        except Device.DoesNotExist:
            raise Http404
        payment_request = payment.prepare_payment(device,
                                                  form.cleaned_data['amount'])
        payment_request.save()
        payment_request_url = self.request.build_absolute_uri(reverse(
            'api:payment_request',
            kwargs={'payment_uid': payment_request.uid}))
        # Create bitcoin uri and QR code
        payment_uri = payment.blockchain.construct_bitcoin_uri(
            payment_request.local_address,
            payment_request.btc_amount,
            payment_request_url)
        qr_code_src = generate_qr_code(payment_uri, size=4)
        payment_check_url = self.request.build_absolute_uri(reverse(
            'api:payment_check',
            kwargs={'payment_uid': payment_request.uid}))
        # Return JSON
        data = {
            'fiat_amount': float(payment_request.fiat_amount),
            'mbtc_amount': float(payment_request.btc_amount / Decimal('0.001')),
            'exchange_rate': float(payment_request.effective_exchange_rate * Decimal('0.001')),
            'payment_uri': payment_uri,
            'qr_code_src': qr_code_src,
            'check_url': payment_check_url,
        }
        response = HttpResponse(json.dumps(data),
                                content_type='application/json')
        return response


class PaymentRequestView(View):
    """
    Send PaymentRequest
    """

    def get(self, *args, **kwargs):
        try:
            payment_request = PaymentRequest.objects.get(uid=self.kwargs.get('payment_uid'))
        except PaymentRequest.DoesNotExist:
            raise Http404
        if payment_request.expires < timezone.now():
            raise Http404
        payment_response_url = self.request.build_absolute_uri(reverse(
            'api:payment_response',
            kwargs={'payment_uid': payment_request.uid}))
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
    Accept and forward payment
    """

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(PaymentResponseView, self).dispatch(*args, **kwargs)

    def post(self, *args, **kwargs):
        try:
            payment_request = PaymentRequest.objects.get(uid=self.kwargs.get('payment_uid'))
        except PaymentRequest.DoesNotExist:
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
            payment.validate_payment(payment_request, transactions)
        except Exception as error:
            return HttpResponseBadRequest()
        # Send PaymentACK
        response = HttpResponse(payment_ack.SerializeToString(),
                                content_type='application/bitcoin-paymentack')
        response['Content-Transfer-Encoding'] = 'binary'
        return response


class PaymentCheckView(View):
    """
    Check payment and return receipt
    """

    def get(self, *args, **kwargs):
        try:
            payment_request = PaymentRequest.objects.get(uid=self.kwargs.get('payment_uid'))
        except PaymentRequest.DoesNotExist:
            raise Http404
        if payment_request.transaction is None:
            data = {'paid': 0}
        else:
            receipt_url = self.request.build_absolute_uri(reverse(
                'api:transaction_pdf',
                kwargs={'key': payment_request.transaction.receipt_key}))
            qr_code_src = generate_qr_code(receipt_url, size=3)
            data = {
                'paid': 1,
                'receipt_url': receipt_url,
                'qr_code_src': qr_code_src,
            }
        response = HttpResponse(json.dumps(data),
                                content_type='application/json')
        return response

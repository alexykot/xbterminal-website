# coding=utf-8
import os

from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from django.http import Http404

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from constance import config

from website.models import Device, Transaction, Firmware
from api.serializers import TransactionSerializer
from api.shotcuts import render_to_pdf


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

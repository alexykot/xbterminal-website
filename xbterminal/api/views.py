# coding=utf-8
from django.shortcuts import get_object_or_404
from django.conf import settings

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView

from website.models import Device, Transaction
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
        "OUR_FEE_BITCOIN_ADDRESS": "1FCrwY2CsLJgsmbogSunECwCa6WswBBrfz",
        "OUR_FEE_SHARE": 0.05,
        "OUTPUT_DEC_FRACTIONAL_SPLIT": device.language.fractional_split,
        "OUTPUT_DEC_THOUSANDS_SPLIT": device.language.thousands_split
    }
    return Response(response)


class CreateTransaction(CreateAPIView):
    model = Transaction
    serializer_class = TransactionSerializer


def transaction_pdf(request, key):
    transaction = get_object_or_404(Transaction, key=key)

    return render_to_pdf(
        'api/transaction.html', {
            'transaction': transaction,
            'STATIC_ROOT': settings.STATIC_ROOT
        }
    )

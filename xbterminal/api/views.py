from decimal import Decimal
import json
import logging

from django.shortcuts import get_object_or_404
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.utils import timezone
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext as _

from rest_framework.decorators import api_view, detail_route
from rest_framework.response import Response
from rest_framework import status, viewsets
from oauth2_provider.views.generic import ProtectedResourceView

from website.models import (
    Device,
    PaymentOrder,
    WithdrawalOrder)
from website.forms import SimpleMerchantRegistrationForm
from website.utils import generate_qr_code, send_registration_info
from api.shortcuts import render_to_pdf
from api.forms import PaymentForm, WithdrawalForm
from api.serializers import WithdrawalOrderSerializer
from api.utils import verify_signature

import operations.payment
import operations.blockchain
import operations.protocol
from operations.instantfiat import gocoin
from operations import withdrawal

logger = logging.getLogger(__name__)


class CSRFExemptMixin(object):

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(CSRFExemptMixin, self).dispatch(*args, **kwargs)


class MerchantView(CSRFExemptMixin, View):

    def post(self, *args, **kwargs):
        """
        Create merchant
        """
        form = SimpleMerchantRegistrationForm(self.request.POST)
        if form.is_valid():
            try:
                merchant = form.save()
            except gocoin.GoCoinNameAlreadyTaken:
                data = {
                    'errors': {'company_name': [_('This company is already registered.')]},
                }
            else:
                send_registration_info(merchant)
                data = {'merchant_id': merchant.pk}
        else:
            data = {'errors': form.errors}
        response = HttpResponse(json.dumps(data),
                                content_type='application/json')
        return response


class DevicesView(ProtectedResourceView):

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
                'percent': float(device.percent),
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
            merchant=merchant)
        device.save()
        data = {
            'name': device.name,
            'key': device.key,
            'percent': float(device.percent),
            'type': device.device_type,
            'online': device.is_online(),
        }
        response = HttpResponse(json.dumps(data),
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


class ReceiptView(View):
    """
    Download PDF receipt
    """
    def get(self, *args, **kwargs):
        order_uid = self.kwargs.get('order_uid')
        try:
            order = PaymentOrder.objects.get(
                Q(uid=order_uid) | Q(receipt_key=order_uid),
                time_finished__isnull=False)
        except PaymentOrder.DoesNotExist:
            try:
                order = WithdrawalOrder.objects.get(
                    uid=order_uid, time_completed__isnull=False)
            except WithdrawalOrder.DoesNotExist:
                raise Http404
        response = render_to_pdf(
            'pdf/receipt.html',
            {'order': order})
        disposition = 'inline; filename="receipt #{0} {1}.pdf"'.format(
            order.id,
            order.device.merchant.company_name)
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
            device = Device.objects.get(key=form.cleaned_data['device_key'])
        except Device.DoesNotExist:
            raise Http404
        payment_order = operations.payment.prepare_payment(
            device, form.cleaned_data['amount'])
        # Urls
        payment_request_url = self.request.build_absolute_uri(reverse(
            'api:short:payment_request',
            kwargs={'payment_uid': payment_order.uid}))
        payment_response_url = self.request.build_absolute_uri(reverse(
            'api:payment_response',
            kwargs={'payment_uid': payment_order.uid}))
        payment_check_url = self.request.build_absolute_uri(reverse(
            'api:payment_check',
            kwargs={'payment_uid': payment_order.uid}))
        # Create payment request
        payment_order.request = operations.protocol.create_payment_request(
            payment_order.device.bitcoin_network,
            [(payment_order.local_address, payment_order.btc_amount)],
            payment_order.time_created,
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
            'payment_uid': payment_order.uid,
            'fiat_amount': float(fiat_amount),
            'btc_amount': float(btc_amount),
            'exchange_rate': float(exchange_rate),
            'check_url': payment_check_url,
        }
        if form.cleaned_data['bt_mac']:
            # Enable payment via bluetooth
            payment_bluetooth_url = 'bt:{mac}'.\
                format(mac=form.cleaned_data['bt_mac'].replace(':', ''))
            payment_bluetooth_request = operations.protocol.create_payment_request(
                payment_order.device.bitcoin_network,
                [(payment_order.local_address, payment_order.btc_amount)],
                payment_order.time_created,
                payment_order.expires,
                payment_bluetooth_url,
                device.merchant.company_name)
            # Send payment request in response
            data['payment_uri'] = operations.blockchain.construct_bitcoin_uri(
                payment_order.local_address,
                payment_order.btc_amount,
                device.merchant.company_name,
                payment_bluetooth_url,
                payment_request_url)
            data['payment_request'] = payment_bluetooth_request.encode('base64')
        else:
            data['payment_uri'] = operations.blockchain.construct_bitcoin_uri(
                payment_order.local_address,
                payment_order.btc_amount,
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
        if len(self.request.body) > 50000:
            # Payment messages larger than 50,000 bytes should be rejected by server
            logger.warning("PaymentResponseView: message is too large")
            return HttpResponseBadRequest()
        try:
            payment_ack = operations.payment.parse_payment(payment_order, self.request.body)
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
            payment_order = PaymentOrder.objects.get(uid=self.kwargs.get('payment_uid'))
        except PaymentOrder.DoesNotExist:
            raise Http404
        if payment_order.is_receipt_ready():
            receipt_url = self.request.build_absolute_uri(reverse(
                'api:short:receipt',
                kwargs={'order_uid': payment_order.uid}))
            qr_code_src = generate_qr_code(receipt_url, size=3)
            data = {
                'paid': 1,
                'receipt_url': receipt_url,
                'qr_code_src': qr_code_src,
            }
            if payment_order.time_finished is None:
                payment_order.time_finished = timezone.now()
                payment_order.save()
        else:
            data = {'paid': 0}
        response = HttpResponse(json.dumps(data),
                                content_type='application/json')
        return response


class WithdrawalViewSet(viewsets.GenericViewSet):

    queryset = WithdrawalOrder.objects.all()
    lookup_field = 'uid'
    serializer_class = WithdrawalOrderSerializer

    def _verify_signature(self, device):
        if not device.api_key:
            return False
        signature = self.request.META.get('HTTP_X_SIGNATURE')
        if not signature:
            return False
        return verify_signature(device.api_key,
                                self.request.body,
                                signature)

    def create(self, request):
        form = WithdrawalForm(data=self.request.data)
        if not form.is_valid():
            return Response({'error': form.error_message},
                            status=status.HTTP_400_BAD_REQUEST)
        if not self._verify_signature(form.cleaned_data['device']):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        try:
            order = withdrawal.prepare_withdrawal(
                form.cleaned_data['device'],
                form.cleaned_data['amount'])
        except withdrawal.WithdrawalError as error:
            return Response({'error': error.message},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @detail_route(methods=['POST'])
    def confirm(self, request, uid=None):
        order = self.get_object()
        if not self._verify_signature(order.device):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        customer_address = self.request.data.get('address')
        try:
            withdrawal.send_transaction(order, customer_address)
        except withdrawal.WithdrawalError as error:
            return Response({'error': error.message},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    def retrieve(self, request, uid=None):
        order = self.get_object()
        if order.time_broadcasted and not order.time_completed:
            # Close order
            order.time_completed = timezone.now()
            order.save()
        serializer = self.get_serializer(order)
        return Response(serializer.data)

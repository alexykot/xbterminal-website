from decimal import Decimal
import logging

from django.conf import settings
from django.http import Http404
from django.utils import timezone

from rest_framework.decorators import list_route, detail_route
from rest_framework.response import Response
from rest_framework import status, viewsets
from constance import config

from website.models import Device, DeviceBatch
from website.utils import generate_qr_code

from api.forms import PaymentForm, WithdrawalForm
from api.serializers import (
    WithdrawalOrderSerializer,
    DeviceSerializer,
    DeviceRegistrationSerializer)
from api.renderers import (
    PlainTextRenderer,
    PDFRenderer,
    PaymentRequestRenderer,
    PaymentACKRenderer)
from api.utils.crypto import verify_signature
from api.utils.pdf import generate_pdf
from api.utils.urls import construct_absolute_url

from operations.models import PaymentOrder, WithdrawalOrder
import operations.payment
import operations.blockchain
import operations.protocol
from operations import withdrawal

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.GenericViewSet):

    queryset = PaymentOrder.objects.all()
    lookup_field = 'uid'

    def create(self, *args, **kwargs):
        form = PaymentForm(data=self.request.data)
        if not form.is_valid():
            return Response({'errors': form.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        # Prepare payment order
        try:
            device = Device.objects.get(key=form.cleaned_data['device_key'],
                                        status='active')
        except Device.DoesNotExist:
            raise Http404
        payment_order = operations.payment.prepare_payment(
            device, form.cleaned_data['amount'])
        # Urls
        payment_request_url = construct_absolute_url(
            'api:v2:payment-request',
            kwargs={'uid': payment_order.uid})
        payment_response_url = construct_absolute_url(
            'api:v2:payment-response',
            kwargs={'uid': payment_order.uid})
        payment_check_url = construct_absolute_url(
            'api:v2:payment-detail',
            kwargs={'uid': payment_order.uid})
        # Create payment request
        payment_order.request = operations.protocol.create_payment_request(
            payment_order.device.bitcoin_network,
            [(payment_order.local_address, payment_order.btc_amount)],
            payment_order.time_created,
            payment_order.expires_at,
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
                payment_order.expires_at,
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
        return Response(data)

    def retrieve(self, *args, **kwargs):
        payment_order = self.get_object()
        if payment_order.time_forwarded is not None:
            # Close order
            data = {'paid': 1}
            if payment_order.time_notified is None:
                payment_order.time_notified = timezone.now()
                payment_order.save()
        else:
            data = {'paid': 0}
        return Response(data)

    @detail_route(methods=['POST'])
    def cancel(self, *args, **kwargs):
        order = self.get_object()
        if order.status != 'new':
            raise Http404
        order.time_cancelled = timezone.now()
        order.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @detail_route(methods=['GET'], renderer_classes=[PaymentRequestRenderer])
    def request(self, *args, **kwargs):
        payment_order = self.get_object()
        if payment_order.status not in ['new', 'underpaid']:
            raise Http404
        response = Response(payment_order.request)
        response['Content-Transfer-Encoding'] = 'binary'
        return response

    @detail_route(methods=['POST'], renderer_classes=[PaymentACKRenderer])
    def response(self, *args, **kwargs):
        payment_order = self.get_object()
        if payment_order.status not in ['new', 'underpaid']:
            raise Http404
        # Check and parse message
        content_type = self.request.META.get('CONTENT_TYPE')
        if content_type != 'application/bitcoin-payment':
            logger.warning("PaymentResponseView: wrong content type")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if len(self.request.body) > 50000:
            # Payment messages larger than 50,000 bytes should be rejected by server
            logger.warning("PaymentResponseView: message is too large")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            payment_ack = operations.payment.parse_payment(payment_order, self.request.body)
        except Exception as error:
            logger.exception(error)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        response = Response(payment_ack)
        response['Content-Transfer-Encoding'] = 'binary'
        return response

    @detail_route(methods=['GET'], renderer_classes=[PDFRenderer])
    def receipt(self, *args, **kwargs):
        order = self.get_object()
        if not order.time_notified:
            raise Http404
        result = generate_pdf('pdf/receipt.html', {'order': order})
        response = Response(result.getvalue())
        response['Content-Disposition'] = 'inline; filename="receipt #{0} {1}.pdf"'.format(
            order.id,
            order.device.merchant.company_name)
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
        if order.status != 'new':
            raise Http404
        customer_address = self.request.data.get('address')
        try:
            withdrawal.send_transaction(order, customer_address)
        except withdrawal.WithdrawalError as error:
            return Response({'error': error.message},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @detail_route(methods=['POST'])
    def cancel(self, *args, **kwargs):
        order = self.get_object()
        if not self._verify_signature(order.device):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        if order.status != 'new':
            raise Http404
        order.time_cancelled = timezone.now()
        order.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, uid=None):
        order = self.get_object()
        if order.time_broadcasted and not order.time_completed:
            # Close order
            order.time_completed = timezone.now()
            order.save()
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @detail_route(methods=['GET'], renderer_classes=[PDFRenderer])
    def receipt(self, *args, **kwargs):
        order = self.get_object()
        if not order.time_completed:
            raise Http404
        result = generate_pdf('pdf/receipt.html', {'order': order})
        response = Response(result.getvalue())
        response['Content-Disposition'] = 'inline; filename="receipt #{0} {1}.pdf"'.format(
            order.id,
            order.device.merchant.company_name)
        return response


class DeviceViewSet(viewsets.GenericViewSet):

    lookup_field = 'key'

    def get_queryset(self):
        queryset = Device.objects.exclude(status='suspended')
        if self.action == 'confirm_activation':
            queryset = queryset.filter(status='activation')
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return DeviceRegistrationSerializer
        elif self.action == 'retrieve':
            return DeviceSerializer

    def retrieve(self, *args, **kwargs):
        device = self.get_object()
        device.last_activity = timezone.now()
        device.save()
        serializer = self.get_serializer(device)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer(data=self.request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        device = serializer.save()
        return Response({'activation_code': device.activation_code})

    @detail_route(methods=['POST'])
    def confirm_activation(self, *args, **kwargs):
        device = self.get_object()
        device.activate()
        device.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DeviceBatchViewSet(viewsets.GenericViewSet):

    lookup_field = 'batch_number'

    def get_queryset(self):
        return DeviceBatch.objects.\
            exclude(batch_number=settings.DEFAULT_BATCH_NUMBER)

    @list_route(methods=['GET'], renderer_classes=[PlainTextRenderer])
    def current(self, *args, **kwargs):
        try:
            batch = self.get_queryset().get(
                batch_number=config.CURRENT_BATCH_NUMBER)
        except DeviceBatch.DoesNotExist:
            raise Http404
        return Response(batch.batch_number)

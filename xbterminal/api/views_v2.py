import datetime
import logging

from django.conf import settings
from django.db.transaction import atomic
from django.http import Http404
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import list_route, detail_route
from rest_framework.response import Response
from rest_framework.views import APIView
from constance import config

from website.models import Device, DeviceBatch
from website.utils.devices import get_device_info

from api.serializers import (
    PaymentInitSerializer,
    PaymentOrderSerializer,
    DepositSerializer,
    WithdrawalInitSerializer,
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

from operations import (
    payment,
    blockchain,
    withdrawal,
    exceptions)
from operations.models import PaymentOrder, WithdrawalOrder
from transactions.models import Deposit
from transactions.deposits import prepare_deposit, handle_bip70_payment

from common import rq_helpers

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.GenericViewSet):

    queryset = PaymentOrder.objects.all()
    lookup_field = 'uid'
    serializer_class = PaymentOrderSerializer

    def create(self, *args, **kwargs):
        serializer = PaymentInitSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        # Prepare payment order
        try:
            order = payment.prepare_payment(
                (serializer.validated_data.get('device') or
                 serializer.validated_data.get('account')),
                serializer.validated_data['amount'])
        except exceptions.PaymentError as error:
            return Response({'device': [error.message]},
                            status=status.HTTP_400_BAD_REQUEST)
        # Urls
        payment_request_url = construct_absolute_url(
            'api:v2:payment-request',
            kwargs={'uid': order.uid})
        # Prepare json response
        data = self.get_serializer(order).data
        if serializer.validated_data.get('bt_mac'):
            # Enable payment via bluetooth
            payment_bluetooth_url = 'bt:{mac}'.\
                format(mac=serializer.validated_data['bt_mac'].replace(':', ''))
            payment_bluetooth_request = order.create_payment_request(
                payment_bluetooth_url)
            # Send payment request in response
            data['payment_uri'] = blockchain.construct_bitcoin_uri(
                order.local_address,
                order.btc_amount,
                order.merchant.company_name,
                payment_bluetooth_url,
                payment_request_url)
            data['payment_request'] = payment_bluetooth_request.encode('base64')
        else:
            data['payment_uri'] = blockchain.construct_bitcoin_uri(
                order.local_address,
                order.btc_amount,
                order.merchant.company_name,
                payment_request_url)
        return Response(data)

    def retrieve(self, *args, **kwargs):
        order = self.get_object()
        if order.time_forwarded and not order.time_notified:
            # Close order
            order.time_notified = timezone.now()
            order.save()
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @detail_route(methods=['POST'])
    @atomic
    def cancel(self, *args, **kwargs):
        order = self.get_object()
        if order.status not in ['new', 'underpaid', 'received']:
            raise Http404
        order.time_cancelled = timezone.now()
        order.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @detail_route(methods=['GET'], renderer_classes=[PaymentRequestRenderer])
    def request(self, *args, **kwargs):
        payment_order = self.get_object()
        if payment_order.status not in ['new', 'underpaid']:
            raise Http404
        payment_response_url = construct_absolute_url(
            'api:v2:payment-response',
            kwargs={'uid': payment_order.uid})
        payment_request = payment_order.create_payment_request(
            payment_response_url)
        response = Response(payment_request)
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
            payment_ack = payment.parse_payment(payment_order, self.request.body)
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
            order.merchant.company_name)
        return response


class DepositViewSet(viewsets.GenericViewSet):

    queryset = Deposit.objects.all()
    lookup_field = 'uid'
    serializer_class = DepositSerializer

    def create(self, *args, **kwargs):
        serializer = PaymentInitSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        # Prepare deposit
        try:
            deposit = prepare_deposit(
                (serializer.validated_data.get('device') or
                 serializer.validated_data.get('account')),
                serializer.validated_data['amount'])
        except exceptions.PaymentError as error:
            return Response({'device': [error.message]},
                            status=status.HTTP_400_BAD_REQUEST)
        # Urls
        payment_request_url = construct_absolute_url(
            'api:v2:deposit-payment-request',
            kwargs={'uid': deposit.uid})
        # Prepare json response
        data = self.get_serializer(deposit).data
        if serializer.validated_data.get('bt_mac'):
            # Enable payment via bluetooth
            payment_bluetooth_url = 'bt:{mac}'.\
                format(mac=serializer.validated_data['bt_mac'].replace(':', ''))
            payment_bluetooth_request = deposit.create_payment_request(
                payment_bluetooth_url)
            # Send payment request in response
            data['payment_uri'] = blockchain.construct_bitcoin_uri(
                deposit.deposit_address.address,
                deposit.coin_amount,
                deposit.merchant.company_name,
                payment_bluetooth_url,
                payment_request_url)
            data['payment_request'] = payment_bluetooth_request.encode('base64')
        else:
            data['payment_uri'] = blockchain.construct_bitcoin_uri(
                deposit.deposit_address.address,
                deposit.coin_amount,
                deposit.merchant.company_name,
                payment_request_url)
        return Response(data)

    def retrieve(self, *args, **kwargs):
        deposit = self.get_object()
        if deposit.time_broadcasted and not deposit.time_notified:
            deposit.time_notified = timezone.now()
            deposit.save()
        serializer = self.get_serializer(deposit)
        return Response(serializer.data)

    @detail_route(methods=['POST'])
    @atomic
    def cancel(self, *args, **kwargs):
        deposit = self.get_object()
        if deposit.status not in ['new', 'underpaid', 'received']:
            raise Http404
        deposit.time_cancelled = timezone.now()
        deposit.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @detail_route(
        methods=['GET'],
        url_name='payment-request',
        url_path='request',
        renderer_classes=[PaymentRequestRenderer])
    def payment_request(self, *args, **kwargs):
        deposit = self.get_object()
        if deposit.status not in ['new', 'underpaid']:
            raise Http404
        payment_response_url = construct_absolute_url(
            'api:v2:deposit-payment-response',
            kwargs={'uid': deposit.uid})
        payment_request = deposit.create_payment_request(
            payment_response_url)
        response = Response(payment_request)
        response['Content-Transfer-Encoding'] = 'binary'
        return response

    @detail_route(
        methods=['POST'],
        url_name='payment-response',
        url_path='response',
        renderer_classes=[PaymentACKRenderer])
    def payment_response(self, *args, **kwargs):
        deposit = self.get_object()
        if deposit.status not in ['new', 'underpaid']:
            raise Http404
        # Check and parse message
        content_type = self.request.META.get('CONTENT_TYPE')
        if content_type != 'application/bitcoin-payment':
            return Response(status=status.HTTP_400_BAD_REQUEST)
        if len(self.request.body) > 50000:
            # Payment messages larger than 50,000 bytes should be rejected by server
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            payment_ack = handle_bip70_payment(deposit, self.request.body)
        except Exception as error:
            logger.exception(error)
            return Response(status=status.HTTP_400_BAD_REQUEST)
        response = Response(payment_ack)
        response['Content-Transfer-Encoding'] = 'binary'
        return response

    @detail_route(methods=['GET'], renderer_classes=[PDFRenderer])
    def receipt(self, *args, **kwargs):
        deposit = self.get_object()
        if not deposit.time_notified:
            raise Http404
        result = generate_pdf('pdf/receipt_deposit.html',
                              {'deposit': deposit})
        response = Response(result.getvalue())
        response['Content-Disposition'] = 'inline; filename="receipt #{0} {1}.pdf"'.format(
            deposit.id,
            deposit.merchant.company_name)
        return response


class WithdrawalViewSet(viewsets.GenericViewSet):

    queryset = WithdrawalOrder.objects.all()
    lookup_field = 'uid'
    serializer_class = WithdrawalOrderSerializer

    def initialize_request(self, request, *args, **kwargs):
        """
        Access body attribute to save POST data in HttpRequest instance
        This allows POST data to be retrieved later for signature checking
        """
        request.body
        return super(WithdrawalViewSet, self).initialize_request(
            request, *args, **kwargs)

    def _verify_signature(self, device):
        if not device.api_key:
            return False
        signature = self.request.META.get('HTTP_X_SIGNATURE')
        if not signature:
            return False
        return verify_signature(device.api_key,
                                self.request.body,
                                signature)

    @atomic
    def create(self, request):
        serializer = WithdrawalInitSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        if not self._verify_signature(serializer.validated_data['device']):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        try:
            order = withdrawal.prepare_withdrawal(
                serializer.validated_data['device'],
                serializer.validated_data['amount'])
        except exceptions.WithdrawalError as error:
            return Response({'device': [error.message]},
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
        except exceptions.WithdrawalError as error:
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
        if order.time_broadcasted and not order.time_notified:
            # Close order
            order.time_notified = timezone.now()
            order.save()
        serializer = self.get_serializer(order)
        return Response(serializer.data)

    @detail_route(methods=['GET'], renderer_classes=[PDFRenderer])
    def receipt(self, *args, **kwargs):
        order = self.get_object()
        if not order.time_notified:
            raise Http404
        result = generate_pdf('pdf/receipt.html', {'order': order})
        response = Response(result.getvalue())
        response['Content-Disposition'] = 'inline; filename="receipt #{0} {1}.pdf"'.format(
            order.id,
            order.merchant.company_name)
        return response


class DeviceViewSet(viewsets.GenericViewSet):

    lookup_field = 'key'

    def get_queryset(self):
        queryset = Device.objects.all()
        if self.action == 'confirm_activation':
            queryset = queryset.filter(status='activation_in_progress')
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return DeviceRegistrationSerializer
        elif self.action == 'retrieve':
            return DeviceSerializer

    def retrieve(self, *args, **kwargs):
        device = self.get_object()
        if not device.is_online() and config.ENABLE_SALT:
            # Get info when device has been turned on
            rq_helpers.run_task(
                get_device_info,
                [device.key],
                queue='low',
                time_delta=datetime.timedelta(minutes=3))
        device.last_activity = timezone.now()
        device.save()
        serializer = self.get_serializer(device)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
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


class PingView(APIView):

    def get(self, *args, **kwargs):
        return Response({'status': 'online'})

from rest_framework import serializers, status, viewsets
from rest_framework.response import Response

from api.serializers import PaymentInitSerializer
from api.utils.urls import construct_absolute_url
from transactions.models import Deposit
from transactions.deposits import prepare_deposit
from operations.exceptions import PaymentError
from operations.blockchain import construct_bitcoin_uri


class DepositSerializer(serializers.ModelSerializer):

    fiat_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        source='amount')
    btc_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=8,
        source='coin_amount')
    paid_btc_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=8,
        source='paid_coin_amount')
    exchange_rate = serializers.DecimalField(
        max_digits=18,
        decimal_places=8,
        source='effective_exchange_rate')

    class Meta:
        model = Deposit
        fields = [
            'uid',
            'fiat_amount',
            'btc_amount',
            'paid_btc_amount',
            'exchange_rate',
            'status',
        ]


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
        except PaymentError as error:
            return Response({'device': [error.message]},
                            status=status.HTTP_400_BAD_REQUEST)
        # Urls
        payment_request_url = construct_absolute_url(
            'api:v2:payment-request',
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
            data['payment_uri'] = construct_bitcoin_uri(
                deposit.deposit_address.address,
                deposit.coin_amount,
                deposit.merchant.company_name,
                payment_bluetooth_url,
                payment_request_url)
            data['payment_request'] = payment_bluetooth_request.encode('base64')
        else:
            data['payment_uri'] = construct_bitcoin_uri(
                deposit.deposit_address.address,
                deposit.coin_amount,
                deposit.merchant.company_name,
                payment_request_url)
        return Response(data)

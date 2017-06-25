from rest_framework import serializers

from transactions.models import Deposit


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

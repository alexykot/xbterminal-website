import re
from rest_framework import serializers

from operations.models import WithdrawalOrder
from website.models import Device, DeviceBatch
from website.validators import validate_public_key


class WithdrawalOrderSerializer(serializers.ModelSerializer):

    btc_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=8)
    exchange_rate = serializers.DecimalField(
        max_digits=18,
        decimal_places=8,
        source='effective_exchange_rate')

    class Meta:
        model = WithdrawalOrder
        fields = [
            'uid',
            'fiat_amount',
            'btc_amount',
            'exchange_rate',
            'status',
        ]


class DeviceRegistrationSerializer(serializers.ModelSerializer):

    batch = serializers.CharField()
    api_key = serializers.CharField(validators=[validate_public_key])
    salt_pubkey_fingerprint = serializers.CharField(required=False)

    class Meta:
        model = Device
        fields = [
            'batch',
            'key',
            'api_key',
            'salt_pubkey_fingerprint',
        ]

    def validate_batch(self, value):
        try:
            batch = DeviceBatch.objects.get(batch_number=value)
        except DeviceBatch.DoesNotExist:
            raise serializers.ValidationError('Invalid batch number.')
        if batch.device_set.count() + 1 > batch.size:
            raise serializers.ValidationError('Registration limit exceeded.')
        return batch

    def validate_key(self, value):
        if not re.match('[0-9a-f]{64}', value):
            raise serializers.ValidationError('Invalid device key.')
        return value

    def create(self, validated_data):
        return Device.objects.create(
            merchant=None,
            device_type='hardware',
            status='activation',
            name='Device {0}'.format(validated_data['key'][:6]),
            **validated_data)

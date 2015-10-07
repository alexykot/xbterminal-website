import re
from rest_framework import serializers

from api.utils.salt import Salt
from operations.models import WithdrawalOrder
from website.models import (
    Language,
    Currency,
    Device,
    DeviceBatch)
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


class DeviceSerializer(serializers.ModelSerializer):

    language = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            'status',
            'bitcoin_network',
            'language',
            'currency',
        ]

    def get_language(self, device):
        if device.status == 'activation':
            language = Language.objects.get(code='en')
        else:
            language = device.merchant.language
        return {
            'code': language.code,
            'fractional_split': language.fractional_split,
            'thousands_split': language.thousands_split,
        }

    def get_currency(self, device):
        if device.status == 'activation':
            currency = Currency.objects.get(name='GBP')
        else:
            currency = device.merchant.currency
        return {
            'name': currency.name,
            'prefix': currency.prefix,
            'postfix': currency.postfix,
        }


class DeviceRegistrationSerializer(serializers.ModelSerializer):

    batch = serializers.CharField()
    key = serializers.CharField()
    api_key = serializers.CharField(validators=[validate_public_key])
    salt_fingerprint = serializers.CharField(required=False)

    class Meta:
        model = Device
        fields = [
            'batch',
            'key',
            'api_key',
            'salt_fingerprint',
        ]

    def __init__(self, *args, **kwargs):
        self._salt = Salt()
        self._salt.login()
        super(DeviceRegistrationSerializer, self).__init__(*args, **kwargs)

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
        if Device.objects.filter(key=value).exists():
            raise serializers.ValidationError('Device is already registered.')
        return value

    def validate(self, data):
        if data.get('salt_fingerprint'):
            # TODO: make salt_fingerprint required field
            if not self._salt.check_fingerprint(data['key'],
                                                data['salt_fingerprint']):
                raise serializers.ValidationError(
                    'Invalid salt key fingerprint.')
        return data

    def create(self, validated_data):
        if validated_data.get('salt_fingerprint'):
            # TODO: make salt_fingerprint required field
            self._salt.accept(validated_data['key'])
        return Device.objects.create(
            merchant=None,
            device_type='hardware',
            status='activation',
            name='Device {0}'.format(validated_data['key'][:6]),
            key=validated_data['key'],
            batch=validated_data['batch'],
            api_key=validated_data['api_key'])

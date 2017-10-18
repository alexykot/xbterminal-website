from decimal import Decimal
import re
from rest_framework import serializers

from api.utils.salt import Salt
from transactions.models import Deposit, Withdrawal
from website.models import (
    Language,
    Currency,
    MerchantAccount,
    Account,
    Device,
    DeviceBatch)
from website.validators import validate_public_key


class MerchantSerializer(serializers.ModelSerializer):

    class Meta:
        model = MerchantAccount
        fields = [
            'id',
            'company_name',
            'contact_first_name',
            'contact_last_name',
            'contact_email',
            'verification_status',
        ]


class DepositInitSerializer(serializers.Serializer):

    device = serializers.CharField(required=False)
    account = serializers.CharField(required=False)
    amount = serializers.DecimalField(
        max_digits=9,
        decimal_places=2,
        min_value=Decimal('0.01'))
    bt_mac = serializers.RegexField(
        '^[0-9a-fA-F:]{17}$',
        required=False)

    def validate_device(self, value):
        try:
            device = Device.objects.get(key=value, status='active')
        except Device.DoesNotExist:
            raise serializers.ValidationError('Invalid device key.')
        return device

    def validate_account(self, value):
        try:
            account = Account.objects.get(pk=value)
        except Account.DoesNotExist:
            raise serializers.ValidationError('Invalid account ID.')
        return account

    def validate(self, data):
        if not data.get('device') and not data.get('account'):
            raise serializers.ValidationError(
                'Either device or account must be specified.')
        return data


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


class WithdrawalInitSerializer(serializers.Serializer):

    device = serializers.CharField()
    amount = serializers.DecimalField(
        max_digits=9,
        decimal_places=2,
        min_value=Decimal('0.01'))

    def validate_device(self, value):
        try:
            return Device.objects.get(key=value,
                                      status='active')
        except Device.DoesNotExist:
            raise serializers.ValidationError('Invalid device key.')


class WithdrawalSerializer(serializers.ModelSerializer):

    fiat_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        source='amount')
    btc_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=8,
        source='coin_amount')
    tx_fee_btc_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=8,
        source='tx_fee_coin_amount')
    exchange_rate = serializers.DecimalField(
        max_digits=18,
        decimal_places=8,
        source='effective_exchange_rate')
    address = serializers.CharField(source='customer_address')

    class Meta:
        model = Withdrawal
        fields = [
            'uid',
            'fiat_amount',
            'btc_amount',
            'tx_fee_btc_amount',
            'exchange_rate',
            'address',
            'status',
        ]


class DeviceSerializer(serializers.ModelSerializer):

    coin = serializers.CharField(
        source='account.currency.name',
        read_only=True)
    bitcoin_network = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    settings = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            'status',
            'coin',
            'bitcoin_network',  # TODO: remove field
            'language',
            'currency',
            'settings',
        ]

    def to_representation(self, device):
        # TODO: remove
        result = super(DeviceSerializer, self).to_representation(device)
        if result['bitcoin_network'] is None:
            del result['bitcoin_network']
        return result

    def get_bitcoin_network(self, device):
        try:
            return device.bitcoin_network
        except ValueError:
            return None

    def get_language(self, device):
        if device.status == 'registered':
            language = Language.objects.get(code='en')
        else:
            language = device.merchant.language
        return {
            'code': language.code,
            'fractional_split': language.fractional_split,
            'thousands_split': language.thousands_split,
        }

    def get_currency(self, device):
        if device.status == 'registered':
            currency = Currency.objects.get(name='GBP')
        else:
            currency = device.merchant.currency
        return {
            'name': currency.name,
            'prefix': currency.prefix,
            'postfix': currency.postfix,
        }

    def get_settings(self, device):
        amount_fields = [
            'amount_1',
            'amount_2',
            'amount_3',
            'amount_shift',
        ]
        result = {}
        for field_name in amount_fields:
            value = getattr(device, field_name)
            result[field_name] = str(value) if value is not None else None
        return result


class DeviceRegistrationSerializer(serializers.ModelSerializer):

    batch = serializers.CharField()
    key = serializers.CharField()
    api_key = serializers.CharField(validators=[validate_public_key])
    salt_fingerprint = serializers.CharField()

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
        if not self._salt.check_fingerprint(data['key'],
                                            data['salt_fingerprint']):
            raise serializers.ValidationError({
                'salt_fingerprint': 'Invalid salt key fingerprint.'})
        return data

    def create(self, validated_data):
        return Device.objects.create(
            merchant=None,
            account=None,
            device_type='hardware',
            status='registered',
            name='Device {0}'.format(validated_data['key'][:6]),
            key=validated_data['key'],
            batch=validated_data['batch'],
            api_key=validated_data['api_key'])

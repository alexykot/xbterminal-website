from decimal import Decimal
import re
from rest_framework import serializers

from api.utils import activation
from api.utils.salt import Salt
from operations.models import PaymentOrder, WithdrawalOrder
from website.models import (
    Language,
    Currency,
    MerchantAccount,
    Account,
    KYCDocument,
    Device,
    DeviceBatch,
    KYC_DOCUMENT_TYPES)
from website.validators import validate_public_key
from website.utils.files import decode_base64


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


class KYCDocumentsSerializer(serializers.Serializer):

    id_document_frontside = serializers.CharField()
    id_document_backside = serializers.CharField()
    residence_document = serializers.CharField()

    def validate_id_document_frontside(self, value):
        try:
            return decode_base64(value), KYC_DOCUMENT_TYPES.ID_FRONT
        except:
            raise serializers.ValidationError('Invalid encoded file.')

    def validate_id_document_backside(self, value):
        try:
            return decode_base64(value), KYC_DOCUMENT_TYPES.ID_BACK
        except:
            raise serializers.ValidationError('Invalid encoded file.')

    def validate_residence_document(self, value):
        try:
            return decode_base64(value), KYC_DOCUMENT_TYPES.ADDRESS
        except:
            raise serializers.ValidationError('Invalid encoded file.')

    def create(self, validated_data):
        uploaded = []
        for file, document_type in validated_data.values():
            document = KYCDocument(merchant=self.context['merchant'],
                                   document_type=document_type)
            document.file.save(file.name, file)
            document.save()
            uploaded.append(document)
        return uploaded


class PaymentInitSerializer(serializers.Serializer):

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

    @property
    def error_message(self):
        for field, errors in self.errors.items():
            if field == 'non_field_errors':
                return errors[0]
            else:
                return '{0} - {1}'.format(field, errors[0]).capitalize()


class PaymentOrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentOrder
        fields = [
            'uid',
            'status',
        ]


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

    status = serializers.SerializerMethodField()
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

    def get_status(self, device):
        if device.status == 'activation':
            return device.status + '_' + activation.get_status(device)
        else:
            return device.status

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

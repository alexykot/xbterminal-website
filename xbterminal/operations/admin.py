from django.contrib import admin
from django.utils.html import format_html

from operations import models
from website.widgets import (
    BitcoinAddressWidget,
    BitcoinTransactionWidget,
    ReadOnlyAdminWidget)
from website.admin import url_to_object
from website.utils import generate_qr_code
from api.utils.urls import construct_absolute_url
from operations.blockchain import construct_bitcoin_uri


class OrderAdminFormMixin(object):
    """
    Read-only admin with address and tx widgets
    """

    def get_form(self, request, obj, **kwargs):
        form = super(OrderAdminFormMixin, self).get_form(request, obj, **kwargs)
        network = obj.bitcoin_network
        for field_name in form.base_fields:
            field = form.base_fields[field_name]
            if field_name.endswith('_address'):
                field.widget = BitcoinAddressWidget(network=network)
            elif field_name.endswith('_tx_id'):
                field.widget = BitcoinTransactionWidget(network=network)
            else:
                field.widget = ReadOnlyAdminWidget(instance=obj)
            field.required = False
            # Field should not allow blank values
            assert not obj._meta.get_field(field_name).blank
        return form


@admin.register(models.PaymentOrder)
class PaymentOrderAdmin(OrderAdminFormMixin, admin.ModelAdmin):

    list_display = [
        '__unicode__',
        'uid',
        'device_link',
        'merchant_link',
        'time_created',
        'status',
    ]

    readonly_fields = ['status', 'payment_request_qr_code']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def device_link(self, payment_order):
        return url_to_object(payment_order.device)

    device_link.allow_tags = True
    device_link.short_description = 'device'

    def merchant_link(self, payment_order):
        return url_to_object(payment_order.device.merchant)

    merchant_link.allow_tags = True
    merchant_link.short_description = 'merchant'

    def payment_request_qr_code(self, payment_order):
        payment_request_url = construct_absolute_url(
            'api:v2:payment-request',
            kwargs={'uid': payment_order.uid})
        payment_uri = construct_bitcoin_uri(
            payment_order.local_address,
            payment_order.btc_amount,
            payment_order.device.merchant.company_name,
            payment_request_url)
        src = generate_qr_code(payment_uri, 4)
        output = format_html('<img src="{0}" alt="{1}">', src, payment_uri)
        return output

    payment_request_qr_code.allow_tags = True


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ['payment_reference']


@admin.register(models.WithdrawalOrder)
class WithdrawalOrderAdmin(OrderAdminFormMixin, admin.ModelAdmin):

    list_display = [
        '__str__',
        'device_link',
        'merchant_link',
        'time_created',
        'status',
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def device_link(self, withdrawal_order):
        return url_to_object(withdrawal_order.device)

    device_link.allow_tags = True
    device_link.short_description = 'device'

    def merchant_link(self, withdrawal_order):
        return url_to_object(withdrawal_order.device.merchant)

    merchant_link.allow_tags = True
    merchant_link.short_description = 'merchant'

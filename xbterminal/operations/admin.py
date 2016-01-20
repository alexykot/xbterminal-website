from django.contrib import admin

from operations import models
from website.widgets import (
    BitcoinAddressWidget,
    BitcoinTransactionWidget,
    ReadOnlyAdminWidget)
from website.admin import url_to_object


class PaymentOrderAdmin(admin.ModelAdmin):

    list_display = [
        '__unicode__',
        'uid',
        'device_link',
        'merchant_link',
        'time_created',
        'status',
    ]

    readonly_fields = ['status']

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

    def get_form(self, request, obj, **kwargs):
        form = super(PaymentOrderAdmin, self).get_form(request, obj, **kwargs)
        network = obj.device.bitcoin_network
        for field_name in form.base_fields:
            field = form.base_fields[field_name]
            if field_name.endswith('address'):
                field.widget = BitcoinAddressWidget(network=network)
            elif field_name.endswith('tx_id'):
                field.widget = BitcoinTransactionWidget(network=network)
            else:
                field.widget = ReadOnlyAdminWidget(instance=obj)
            field.required = False
        return form


class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ['payment_reference']


class WithdrawalOrderAdmin(admin.ModelAdmin):

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

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.opts.local_fields]

    def device_link(self, withdrawal_order):
        return url_to_object(withdrawal_order.device)

    device_link.allow_tags = True
    device_link.short_description = 'device'

    def merchant_link(self, withdrawal_order):
        return url_to_object(withdrawal_order.device.merchant)

    merchant_link.allow_tags = True
    merchant_link.short_description = 'merchant'


admin.site.register(models.PaymentOrder, PaymentOrderAdmin)
admin.site.register(models.Order, OrderAdmin)
admin.site.register(models.WithdrawalOrder, WithdrawalOrderAdmin)

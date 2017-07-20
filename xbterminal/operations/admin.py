from django.contrib import admin
from django.utils.html import format_html

from operations import models
from website.models import Transaction
from website.widgets import (
    BitcoinAddressWidget,
    BitcoinTransactionWidget,
    BitcoinTransactionArrayWidget,
    ReadOnlyAdminWidget)
from website.utils.qr import generate_qr_code
from api.utils.urls import construct_absolute_url, get_link_to_object
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
            elif field_name.endswith('_tx_ids'):
                field.widget = BitcoinTransactionArrayWidget(network=network)
            else:
                field.widget = ReadOnlyAdminWidget(instance=obj)
            field.required = False
            # Field should not allow blank values
            assert not obj._meta.get_field(field_name).blank
        return form


class TransactionInline(admin.TabularInline):

    model = Transaction
    exclude = [
        'payment',
        'withdrawal',
        # 'amount',
        'instantfiat_tx_id',
    ]
    readonly_fields = [
        'amount_colored',
        'tx_hash',
        'is_confirmed',
        'instantfiat_tx_id',
        'order',
        'created_at',
    ]
    max_num = 0
    extra = 0
    can_delete = False

    def amount_colored(self, obj):
        template = '<span style="color: {0}">{1}</span>'
        return format_html(template,
                           'red' if obj.amount < 0 else 'green',
                           obj.amount)
    amount_colored.allow_tags = True
    amount_colored.short_description = 'amount'

    def order(self, obj):
        if obj.payment:
            return get_link_to_object(obj.payment)
        elif obj.withdrawal:
            return get_link_to_object(obj.withdrawal)
        else:
            return '-'
    order.allow_tags = True


class PaymentOrderTransactionInline(TransactionInline):

    exclude = ['withdrawal', 'amount', 'instantfiat_tx_id']
    readonly_fields = ['account', 'amount_colored']


class PaymentOrderStatusListFilter(admin.SimpleListFilter):

    title = 'status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('unconfirmed', 'Unconfirmed'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'unconfirmed':
            return queryset.filter(time_notified__isnull=False,
                                   time_confirmed__isnull=True)


@admin.register(models.PaymentOrder)
class PaymentOrderAdmin(OrderAdminFormMixin, admin.ModelAdmin):

    list_display = [
        '__str__',
        'device_link',
        'account_link',
        'merchant_link',
        'time_created',
        'status',
    ]
    list_filter = [PaymentOrderStatusListFilter]
    readonly_fields = ['status', 'payment_request_qr_code']
    inlines = [PaymentOrderTransactionInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def device_link(self, payment_order):
        if payment_order.device:
            return get_link_to_object(payment_order.device)
        else:
            return '-'
    device_link.allow_tags = True
    device_link.short_description = 'device'

    def account_link(self, payment_order):
        if payment_order.account:
            return get_link_to_object(payment_order.account)
        else:
            return '-'

    account_link.allow_tags = True
    account_link.short_description = 'account'

    def merchant_link(self, payment_order):
        return get_link_to_object(payment_order.merchant)

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


class WithdrawalOrderTransactionInline(TransactionInline):

    exclude = ['payment', 'amount', 'instantfiat_tx_id']
    readonly_fields = ['account', 'amount_colored']


@admin.register(models.WithdrawalOrder)
class WithdrawalOrderAdmin(OrderAdminFormMixin, admin.ModelAdmin):

    list_display = [
        '__str__',
        'device_link',
        'account_link',
        'merchant_link',
        'time_created',
        'status',
    ]
    readonly_fields = ['status']
    inlines = [WithdrawalOrderTransactionInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def device_link(self, withdrawal_order):
        if withdrawal_order.device:
            return get_link_to_object(withdrawal_order.device)
        else:
            return '-'

    device_link.allow_tags = True
    device_link.short_description = 'device'

    def account_link(self, withdrawal_order):
        if withdrawal_order.account:
            return get_link_to_object(withdrawal_order.account)
        else:
            return '-'

    account_link.allow_tags = True
    account_link.short_description = 'account'

    def merchant_link(self, withdrawal_order):
        return get_link_to_object(withdrawal_order.merchant)

    merchant_link.allow_tags = True
    merchant_link.short_description = 'merchant'

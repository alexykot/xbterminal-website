from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from transactions import models
from operations.services import blockcypher
from api.utils.urls import get_link_to_object


def get_address_link(address, bitcoin_network):
    if not address:
        return '-'
    return format_html(
        '<a target="_blank" href="{0}">{1}</a>',
        blockcypher.get_address_url(address, bitcoin_network),
        address)


def get_tx_link(tx_id, bitcoin_network):
    if not tx_id:
        return '-'
    return format_html(
        '<a target="_blank" href="{0}">{1}</a><br>',
        blockcypher.get_tx_url(tx_id, bitcoin_network),
        tx_id)


@admin.register(models.Deposit)
class DepositAdmin(admin.ModelAdmin):

    list_display = [
        '__str__',
        'uid',
        'device_link',
        'account_link',
        'merchant_link',
        'time_created',
        'status',
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = []
        for field in self.model._meta.get_fields():
            if field.name == 'balancechange':
                continue
            if field.name in ['deposit_address', 'refund_address',
                              'incoming_tx_ids', 'refund_tx_id']:
                readonly_fields.append(field.name + '_widget')
            else:
                readonly_fields.append(field.name)
        readonly_fields += ['status', 'coin_amount']
        return readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        """
        Remove all fields from the admin form
        """
        form = super(DepositAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields.clear()
        return form

    def device_link(self, deposit):
        if deposit.device:
            return get_link_to_object(deposit.device)
        else:
            return '-'

    device_link.allow_tags = True
    device_link.short_description = 'device'

    def account_link(self, deposit):
        return get_link_to_object(deposit.account)

    account_link.allow_tags = True
    account_link.short_description = 'account'

    def merchant_link(self, deposit):
        return get_link_to_object(deposit.merchant)

    merchant_link.allow_tags = True
    merchant_link.short_description = 'merchant'

    def deposit_address_widget(self, deposit):
        return get_address_link(deposit.deposit_address.address,
                                deposit.bitcoin_network)

    deposit_address_widget.short_description = 'deposit address'

    def refund_address_widget(self, deposit):
        return get_address_link(deposit.refund_address,
                                deposit.bitcoin_network)

    refund_address_widget.short_description = 'refund address'

    def incoming_tx_ids_widget(self, deposit):
        links = [get_tx_link(tx_id, deposit.bitcoin_network)
                 for tx_id in deposit.incoming_tx_ids]
        if not links:
            return '-'
        return mark_safe('<br>'.join(links))  # nosec

    incoming_tx_ids_widget.short_description = 'incoming tx IDs'

    def refund_tx_id_widget(self, deposit):
        return get_tx_link(deposit.refund_tx_id,
                           deposit.bitcoin_network)

    refund_tx_id_widget.short_description = 'refund tx ID'


@admin.register(models.BalanceChange)
class BalanceChangeAdmin(admin.ModelAdmin):

    list_display = [
        '__str__',
        'account_link',
        'address_link',
        'amount_colored',
    ]

    readonly_fields = [
        'deposit',
        'account',
        'address',
        'amount',
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def account_link(self, change):
        if change.account:
            return get_link_to_object(change.account)
        else:
            return '-'

    account_link.short_description = 'account'

    def address_link(self, change):
        return get_link_to_object(change.address)

    address_link.short_description = 'address'

    def amount_colored(self, change):
        template = '<span style="color: {0}">{1}</span>'
        return format_html(template,
                           'red' if change.amount < 0 else 'green',
                           change.amount)

    amount_colored.allow_tags = True
    amount_colored.short_description = 'amount'
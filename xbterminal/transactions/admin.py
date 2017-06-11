from django.contrib import admin
from django.utils.html import format_html

from transactions import models
from operations.services import blockcypher
from api.utils.urls import get_link_to_object


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
            if field.name == 'deposit_address':
                readonly_fields.append(field.name + '_link')
            else:
                readonly_fields.append(field.name)
        readonly_fields += ['status']
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

    def deposit_address_link(self, deposit):
        address = deposit.deposit_address.address
        output = format_html(
            '<a target="_blank" href="{0}">{1}</a>',
            blockcypher.get_address_url(address, deposit.bitcoin_network),
            address)
        return output

    deposit_address_link.short_description = 'deposit address'

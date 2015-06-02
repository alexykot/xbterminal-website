from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.urlresolvers import reverse
from django.utils.html import format_html

from website import forms, models
from website.utils import generate_qr_code
from website.widgets import (
    BitcoinAddressWidget,
    BitcoinTransactionWidget,
    ReadOnlyAdminWidget)


def url_to_object(obj):
    url_name = u'admin:{0}_{1}_change'.format(
        obj._meta.app_label, obj._meta.module_name)
    return format_html(u'<a href="{0}">{1}</a>',
                       reverse(url_name, args=[obj.pk]),
                       str(obj))


class DeviceAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'is_online', 'merchant_link')
    readonly_fields = [
        'key',
        'device_key_qr_code',
        'last_reconciliation',
        'payment_processor',
        'is_online',
    ]
    form = forms.DeviceAdminForm

    def payment_processor(self, device):
        return device.merchant.get_payment_processor_display()

    def merchant_link(self, device):
        return url_to_object(device.merchant)

    merchant_link.allow_tags = True
    merchant_link.short_description = 'merchant'

    def device_key_qr_code(self, device):
        src = generate_qr_code(device.key, 4)
        output = format_html('<img src="{0}" alt="{1}">', src, device.key)
        return output

    device_key_qr_code.allow_tags = True


class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        '__unicode__',
        'paymentorder',
        'device_link',
        'merchant_link',
        'date_created',
    ]
    readonly_fields = ['receipt_key']

    def device_link(self, transaction):
        return url_to_object(transaction.device)

    device_link.allow_tags = True
    device_link.short_description = 'device'

    def merchant_link(self, transaction):
        return url_to_object(transaction.device.merchant)

    merchant_link.allow_tags = True
    merchant_link.short_description = 'merchant'


class FirmwareAdmin(admin.ModelAdmin):
    list_display = ('id', 'version', 'hash', 'added')
    readonly_fields = ('hash',)


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

    def has_add_permission(self, request, obj=None):
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


class UserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                    'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}
        ),
    )
    form = forms.UserChangeForm
    add_form = forms.UserCreationForm
    list_display = ('email', 'merchant_link', 'is_staff')
    search_fields = ('email',)
    ordering = ('email',)

    def merchant_link(self, user):
        if not hasattr(user, 'merchant'):
            return u'-'
        return url_to_object(user.merchant)

    merchant_link.allow_tags = True
    merchant_link.short_description = 'merchant account'


class KYCDocumentAdmin(admin.ModelAdmin):

    list_display = ['__unicode__', 'merchant', 'status']
    readonly_fields = ['uploaded']


class KYCDocumentInline(admin.TabularInline):

    model = models.KYCDocument
    extra = 0


class BTCAccountAdmin(admin.ModelAdmin):

    readonly_fields = ['balance', 'address']


class BTCAccountInline(admin.TabularInline):

    model = models.BTCAccount
    readonly_fields = ['balance', 'address']
    extra = 1


class MerchantAccountAdmin(admin.ModelAdmin):

    list_display = [
        '__unicode__',
        'id',
        'user_link',
        'trading_name',
        'country_code',
        'contact_name',
        'contact_phone_',
        'verification_status',
        'processing',
        'btc_balance',
        'tbtc_balance',
        'date_joined_l',
    ]
    readonly_fields = ['date_joined', 'last_login']
    ordering = ['id']

    inlines = [
        BTCAccountInline,
        KYCDocumentInline,
    ]

    def date_joined(self, merchant):
        return merchant.user.date_joined.strftime('%d %b %Y %l:%M %p')

    def date_joined_l(self, merchant):
        return merchant.user.date_joined.strftime('%d %b %Y')

    date_joined_l.admin_order_field = 'user__date_joined'
    date_joined_l.short_description = 'date joined'

    def last_login(self, merchant):
        return merchant.user.last_login.strftime('%d %b %Y %l:%M %p')

    def user_link(self, merchant):
        return url_to_object(merchant.user)

    user_link.allow_tags = True
    user_link.short_description = 'user'

    def country_code(self, merchant):
        return merchant.country.code

    country_code.short_description = ''

    def contact_name(self, merchant):
        return merchant.contact_first_name + ' ' + merchant.contact_last_name

    contact_name.short_description = 'name'

    def contact_phone_(self, merchant):
        return merchant.contact_phone

    contact_phone_.short_description = 'phone'

    def btc_balance(self, merchant):
        value = merchant.get_account_balance('mainnet')
        return '{0:.8f}'.format(value) if value is not None else 'N/A'
    btc_balance.short_description = 'BTC balance'

    def tbtc_balance(self, merchant):
        value = merchant.get_account_balance('testnet')
        return '{0:.8f}'.format(value) if value is not None else 'N/A'
    tbtc_balance.short_description = 'TBTC balance'

    def processing(self, merchant):
        return '{0}, {1}'.format(
            merchant.get_payment_processor_display(),
            str(bool(merchant.api_key)))


class WithdrawalOrderAdmin(admin.ModelAdmin):

    list_display = [
        '__str__',
        'device_link',
        'merchant_link',
        'time_created',
        'status',
    ]

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.opts.local_fields]

    def device_link(self, payment_order):
        return url_to_object(payment_order.device)
    device_link.allow_tags = True
    device_link.short_description = 'device'

    def merchant_link(self, payment_order):
        return url_to_object(payment_order.device.merchant)
    merchant_link.allow_tags = True
    merchant_link.short_description = 'merchant'


admin.site.register(models.User, UserAdmin)
admin.site.register(models.MerchantAccount, MerchantAccountAdmin)
admin.site.register(models.BTCAccount, BTCAccountAdmin)
admin.site.register(models.KYCDocument, KYCDocumentAdmin)
admin.site.register(models.Device, DeviceAdmin)
admin.site.register(models.Language)
admin.site.register(models.Currency)
admin.site.register(models.Transaction, TransactionAdmin)
admin.site.register(models.Firmware, FirmwareAdmin)
admin.site.register(models.PaymentOrder, PaymentOrderAdmin)
admin.site.register(models.Order, OrderAdmin)
admin.site.register(models.WithdrawalOrder, WithdrawalOrderAdmin)

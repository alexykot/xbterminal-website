from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.urlresolvers import reverse
from django.utils.html import format_html

from website import forms, models


def url_to_object(obj):
    url_name = 'admin:{0}_{1}_change'.format(
        obj._meta.app_label, obj._meta.module_name)
    return format_html('<a href="{0}">{1}</a>',
                       reverse(url_name, args=[obj.pk]),
                       str(obj))


class DeviceAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'is_online', 'merchant_link')
    readonly_fields = [
        'key',
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


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'device_link', 'merchant_link', 'date_created')
    readonly_fields = ('receipt_key',)

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
        'device_link',
        'merchant_link',
        'transaction_link',
        'created',
    ]

    def transaction_link(self, payment_order):
        if not payment_order.transaction:
            return u'-'
        return url_to_object(payment_order.transaction)

    transaction_link.allow_tags = True
    transaction_link.short_description = 'transaction'

    def device_link(self, payment_order):
        return url_to_object(payment_order.device)

    device_link.allow_tags = True
    device_link.short_description = 'device'

    def merchant_link(self, payment_order):
        return url_to_object(payment_order.device.merchant)

    merchant_link.allow_tags = True
    merchant_link.short_description = 'merchant'


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
        'date_joined_l',
    ]
    readonly_fields = ['date_joined', 'last_login']
    ordering = ['id']

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

    def processing(self, merchant):
        return '{0}, {1}'.format(
            merchant.get_payment_processor_display(),
            str(bool(merchant.api_key)))


admin.site.register(models.User, UserAdmin)
admin.site.register(models.MerchantAccount, MerchantAccountAdmin)
admin.site.register(models.Device, DeviceAdmin)
admin.site.register(models.Language)
admin.site.register(models.Currency)
admin.site.register(models.Transaction, TransactionAdmin)
admin.site.register(models.Firmware, FirmwareAdmin)
admin.site.register(models.PaymentOrder, PaymentOrderAdmin)
admin.site.register(models.Order, OrderAdmin)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.urlresolvers import reverse

from website import forms, models


def url_to_object(obj):
    url_name = 'admin:{0}_{1}_change'.format(
        obj._meta.app_label, obj._meta.module_name)
    return u'<a href="{0}">{1}</a>'.format(
        reverse(url_name, args=[obj.pk]), str(obj))


class DeviceAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'is_online', 'merchant')
    readonly_fields = ('key', 'last_reconciliation', 'payment_processor')
    form = forms.DeviceAdminForm

    def payment_processor(self, device):
        return device.merchant.get_payment_processor_display()


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'device', 'date_created')
    readonly_fields = ('receipt_key',)


class FirmwareAdmin(admin.ModelAdmin):
    list_display = ('id', 'version', 'hash', 'added')
    readonly_fields = ('hash',)


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
    merchant_link.short_description = "merchant account"


class MerchantAccountAdmin(admin.ModelAdmin):

    readonly_fields = ['date_joined', 'last_login']

    def date_joined(self, merchant):
        return merchant.user.date_joined.strftime('%d %b %Y %l:%M %p')

    def last_login(self, merchant):
        return merchant.user.last_login.strftime('%d %b %Y %l:%M %p')


admin.site.register(models.User, UserAdmin)
admin.site.register(models.MerchantAccount, MerchantAccountAdmin)
admin.site.register(models.Device, DeviceAdmin)
admin.site.register(models.Language)
admin.site.register(models.Currency)
admin.site.register(models.Transaction, TransactionAdmin)
admin.site.register(models.Firmware, FirmwareAdmin)
admin.site.register(models.PaymentOrder)
admin.site.register(models.Order, OrderAdmin)

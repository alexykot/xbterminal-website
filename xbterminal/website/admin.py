from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from website import forms, models


class DeviceAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'is_online', 'merchant')
    readonly_fields = ('key', 'last_reconciliation')
    form = forms.DeviceAdminForm


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
    list_display = ('email', 'is_staff')
    search_fields = ('email',)
    ordering = ('email',)


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

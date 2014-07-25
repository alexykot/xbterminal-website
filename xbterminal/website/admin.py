from django.contrib import admin

from website import forms, models


class DeviceAdmin(admin.ModelAdmin):
    readonly_fields = ('key', 'last_reconciliation')
    form = forms.DeviceAdminForm


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'device', 'date_created')
    readonly_fields = ('receipt_key',)


class FirmwareAdmin(admin.ModelAdmin):
    list_display = ('id', 'version', 'hash', 'added')
    readonly_fields = ('hash',)


admin.site.register(models.MerchantAccount)
admin.site.register(models.Device, DeviceAdmin)
admin.site.register(models.Language)
admin.site.register(models.Currency)
admin.site.register(models.Transaction, TransactionAdmin)
admin.site.register(models.Firmware, FirmwareAdmin)
admin.site.register(models.PaymentOrder)
admin.site.register(models.Order)

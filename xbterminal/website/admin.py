from django.contrib import admin

from website.models import (MerchantAccount, Device, Language, Currency, Transaction,
                            Firmware)
from website.forms import DeviceAdminForm


class DeviceAdmin(admin.ModelAdmin):
    readonly_fields = ('key', 'email', 'time', 'date')
    form = DeviceAdminForm


class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'device', 'date_created')
    readonly_fields = ('receipt_key',)


class FirmwareAdmin(admin.ModelAdmin):
    list_display = ('id', 'version', 'hash', 'added')
    readonly_fields = ('hash',)


admin.site.register(MerchantAccount)
admin.site.register(Device, DeviceAdmin)
admin.site.register(Language)
admin.site.register(Currency)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Firmware, FirmwareAdmin)

from django.contrib import admin

from website.models import MerchantAccount, Device, Language, Currency, Transaction


class DeviceAdmin(admin.ModelAdmin):
    readonly_fields = ('key',)


class TransactionAdmin(admin.ModelAdmin):
    readonly_fields = ('key',)


admin.site.register(MerchantAccount)
admin.site.register(Device, DeviceAdmin)
admin.site.register(Language)
admin.site.register(Currency)
admin.site.register(Transaction, TransactionAdmin)

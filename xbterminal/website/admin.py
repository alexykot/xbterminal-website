from django.contrib import admin
from website.models import MerchantAccount, Contact, Device


class ContactAdmin(admin.ModelAdmin):
    readonly_fields = ('add_date',)

admin.site.register(MerchantAccount)
admin.site.register(Contact, ContactAdmin)
admin.site.register(Device)

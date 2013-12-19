from django.contrib import admin
from website.models import MerchantAccount, Contact


class ContactAdmin(admin.ModelAdmin):
    readonly_fields = ('add_date',)

admin.site.register(MerchantAccount)
admin.site.register(Contact, ContactAdmin)

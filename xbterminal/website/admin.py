from django.contrib import admin

from website.models import MerchantAccount, Device, Language, Currency


admin.site.register(MerchantAccount)
admin.site.register(Device)
admin.site.register(Language)
admin.site.register(Currency)

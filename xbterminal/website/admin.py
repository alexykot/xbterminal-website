from django.contrib import admin
from website.models import MerchantAccount, MerchantAccountAddress, Contact

admin.site.register(MerchantAccount)
admin.site.register(MerchantAccountAddress)
admin.site.register(Contact)

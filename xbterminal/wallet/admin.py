from django.contrib import admin

from wallet import models


@admin.register(models.WalletKey)
class WalletKeyAdmin(admin.ModelAdmin):

    list_display = [
        '__str__',
        'coin_type',
    ]
    readonly_fields = [
        'coin_type',
        'private_key',
        'path',
        'added_at',
    ]

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return self.readonly_fields
        else:
            return []

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.WalletAccount)
class WalletAccountAdmin(admin.ModelAdmin):

    list_display = [
        '__str__',
        'addresses',
    ]
    readonly_fields = [
        'parent_key',
        'index',
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def addresses(self, obj):
        return obj.address_set.count()


@admin.register(models.Address)
class AddressAdmin(admin.ModelAdmin):

    list_display = [
        '__str__',
        'is_change',
        'index',
    ]
    readonly_fields = [
        'wallet_account',
        'is_change',
        'index',
        'address',
    ]
    list_filter = ['wallet_account__parent_key__coin_type']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

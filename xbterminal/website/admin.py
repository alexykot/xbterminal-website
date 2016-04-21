from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.urlresolvers import reverse
from django.utils.html import format_html

from fsm_admin.mixins import FSMTransitionMixin

from website import forms, models
from website.utils import generate_qr_code
from website.widgets import BitcoinAddressWidget


def url_to_object(obj):
    url_name = u'admin:{0}_{1}_change'.format(
        obj._meta.app_label, obj._meta.model_name)
    return format_html(u'<a href="{0}">{1}</a>',
                       reverse(url_name, args=[obj.pk]),
                       str(obj))


@admin.register(models.Language)
class LanguageAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.Currency)
class CurrencyAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.Device)
class DeviceAdmin(FSMTransitionMixin, admin.ModelAdmin):

    list_display = [
        '__unicode__',
        'merchant_link',
        'account_link',
        'device_type',
        'status',
        'last_activity',
        'is_online',
    ]
    readonly_fields = [
        'status',
        'key',
        'device_key_qr_code',
        'activation_code',
        'last_reconciliation',
        'payment_processor',
        'is_online',
    ]
    fsm_field = ['status']
    form = forms.DeviceAdminForm

    def payment_processor(self, device):
        if device.status == 'registered':
            return '-'
        else:
            return device.merchant.get_payment_processor_display()

    def merchant_link(self, device):
        if device.status == 'registered':
            return '-'
        else:
            return url_to_object(device.merchant)
    merchant_link.allow_tags = True
    merchant_link.short_description = 'merchant'

    def account_link(self, device):
        if not device.account:
            return '-'
        else:
            return url_to_object(device.account)
    account_link.allow_tags = True
    account_link.short_description = 'account'

    def device_key_qr_code(self, device):
        src = generate_qr_code(device.key, 4)
        output = format_html('<img src="{0}" alt="{1}">', src, device.key)
        return output

    device_key_qr_code.allow_tags = True


@admin.register(models.User)
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
            'fields': ('email', 'password1', 'password2'),
        }),
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
    merchant_link.short_description = 'merchant account'


@admin.register(models.KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):

    list_display = ['__unicode__', 'merchant', 'status']
    readonly_fields = ['uploaded']


class KYCDocumentInline(admin.TabularInline):

    model = models.KYCDocument
    extra = 0


@admin.register(models.Account)
class AccountAdmin(admin.ModelAdmin):

    list_display = [
        '__unicode__',
        'balance',
        'balance_max',
        'instantfiat_provider',
    ]

    def get_form(self, request, obj, **kwargs):
        form = super(AccountAdmin, self).get_form(request, obj, **kwargs)
        if not obj:
            return form
        for field_name in form.base_fields:
            field = form.base_fields[field_name]
            if field_name == 'bitcoin_address':
                if obj.currency.name == 'BTC':
                    field.widget = BitcoinAddressWidget(network='mainnet')
                elif obj.currency.name == 'TBTC':
                    field.widget = BitcoinAddressWidget(network='testnet')
                field.required = True
                # Workaround for address field with blank=True
                field.clean = lambda *args: obj.bitcoin_address
        return form


class AccountInline(admin.TabularInline):

    model = models.Account
    readonly_fields = ['bitcoin_address']
    extra = 1


@admin.register(models.MerchantAccount)
class MerchantAccountAdmin(admin.ModelAdmin):

    list_display = [
        '__unicode__',
        'id',
        'user_link',
        'trading_name',
        'country_code',
        'contact_name',
        'contact_phone_',
        'verification_status',
        'processing',
        'btc_balance',
        'tbtc_balance',
        'date_joined_l',
    ]
    readonly_fields = ['date_joined', 'last_login']
    ordering = ['id']

    inlines = [
        AccountInline,
        KYCDocumentInline,
    ]

    def date_joined(self, merchant):
        return merchant.user.date_joined.strftime('%d %b %Y %l:%M %p')

    def date_joined_l(self, merchant):
        return merchant.user.date_joined.strftime('%d %b %Y')

    date_joined_l.admin_order_field = 'user__date_joined'
    date_joined_l.short_description = 'date joined'

    def last_login(self, merchant):
        return merchant.user.last_login.strftime('%d %b %Y %l:%M %p')

    def user_link(self, merchant):
        return url_to_object(merchant.user)

    user_link.allow_tags = True
    user_link.short_description = 'user'

    def country_code(self, merchant):
        return merchant.country.code

    country_code.short_description = ''

    def contact_name(self, merchant):
        return merchant.contact_first_name + ' ' + merchant.contact_last_name

    contact_name.short_description = 'name'

    def contact_phone_(self, merchant):
        return merchant.contact_phone

    contact_phone_.short_description = 'phone'

    def btc_balance(self, merchant):
        value = merchant.get_account_balance('BTC')
        return '{0:.8f}'.format(value) if value is not None else 'N/A'
    btc_balance.short_description = 'BTC balance'

    def tbtc_balance(self, merchant):
        value = merchant.get_account_balance('TBTC')
        return '{0:.8f}'.format(value) if value is not None else 'N/A'
    tbtc_balance.short_description = 'TBTC balance'

    def processing(self, merchant):
        return '{0}, {1}'.format(
            merchant.get_payment_processor_display(),
            str(bool(merchant.api_key)))


@admin.register(models.DeviceBatch)
class DeviceBatchAdmin(admin.ModelAdmin):

    list_display = [
        '__unicode__',
        'devices',
    ]
    readonly_fields = ['batch_number']

    def devices(self, batch):
        return '{0}/{1}'.format(
            batch.device_set.count(),
            batch.size)


admin.site.register(models.UITheme)

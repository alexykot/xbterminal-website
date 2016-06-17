from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from constance import config
from fsm_admin.mixins import FSMTransitionMixin

from website import forms, models
from website.utils.qr import generate_qr_code
from website.widgets import BitcoinAddressWidget
from operations.instantfiat import cryptopay
from api.utils.urls import get_admin_url


def url_to_object(obj):
    return format_html(u'<a href="{0}">{1}</a>',
                       get_admin_url(obj, absolute=False),
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
        'is_online',
    ]
    fsm_field = ['status']
    form = forms.DeviceAdminForm

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

    list_display = [
        '__unicode__',
        'merchant',
        'original_name',
        'status',
        'uploaded_at',
    ]
    readonly_fields = ['uploaded_at']


class KYCDocumentInline(admin.TabularInline):

    model = models.KYCDocument
    extra = 0


class AddressInline(admin.TabularInline):

    model = models.Address
    max_num = 0
    extra = 0
    can_delete = 0

    def get_formset(self, request, obj, **kwargs):
        formset = super(AddressInline, self).get_formset(
            request, obj, **kwargs)
        if not obj:
            return formset
        for field_name in formset.form.base_fields:
            field = formset.form.base_fields[field_name]
            if field_name == 'address':
                field.widget = BitcoinAddressWidget(network=obj.bitcoin_network)
                field.required = False
        return formset


class TransactionInline(admin.TabularInline):

    model = models.Transaction
    exclude = [
        'payment',
        'withdrawal',
        # 'amount',
        'instantfiat_tx_id',
    ]
    readonly_fields = [
        'amount_colored',
        'tx_hash',
        'is_confirmed',
        'instantfiat_tx_id',
        'order',
        'created_at',
    ]
    max_num = 0
    extra = 0
    can_delete = False

    def amount_colored(self, obj):
        template = '<span style="color: {0}">{1}</span>'
        return format_html(template,
                           'red' if obj.amount < 0 else 'green',
                           obj.amount)
    amount_colored.allow_tags = True
    amount_colored.short_description = 'amount'

    def order(self, obj):
        if obj.payment:
            return url_to_object(obj.payment)
        elif obj.withdrawal:
            return url_to_object(obj.withdrawal)
        else:
            return '-'
    order.allow_tags = True


@admin.register(models.Account)
class AccountAdmin(admin.ModelAdmin):

    readonly_fields = [
        'balance',
        'balance_confirmed',
    ]
    list_display = [
        'id',
        'merchant',
        'currency',
        'balance',
        'balance_confirmed',
        'balance_min',
        'balance_max',
        'payment_processor',
    ]
    list_filter = ['instantfiat']
    inlines = [
        AddressInline,
        TransactionInline,
    ]

    def payment_processor(self, obj):
        if obj.instantfiat:
            return obj.merchant.get_instantfiat_provider_display()
        else:
            return '-'


class AccountInline(admin.TabularInline):

    model = models.Account
    exclude = [
        'bitcoin_address',
        'forward_address',
        'instantfiat_account_id',
    ]
    readonly_fields = [
        'currency',
        'instantfiat',
        'balance',
    ]
    extra = 0
    max_num = 0
    can_delete = False

    def get_formset(self, *args, **kwargs):
        # Disable form validation
        formset = super(AccountInline, self).get_formset(*args, **kwargs)
        formset.form._post_clean = lambda *args: None
        return formset


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
        'date_joined_l',
        'can_activate_device',
    ]
    readonly_fields = ['date_joined', 'last_login']
    ordering = ['id']

    inlines = [
        AccountInline,
        KYCDocumentInline,
    ]
    actions = ['reset_cryptopay_password']

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

    def reset_cryptopay_password(self, request, queryset):
        for merchant in queryset:
            if merchant.instantfiat_provider != \
                    models.INSTANTFIAT_PROVIDERS.CRYPTOPAY or \
                    not merchant.instantfiat_merchant_id:
                self.message_user(
                    request,
                    'Merchant "{0}" doesn\'t have managed CryptoPay profile.'.format(
                        merchant.company_name),
                    messages.WARNING)
                continue
            password = models.User.objects.make_random_password(16)
            try:
                cryptopay.set_password(
                    merchant.instantfiat_merchant_id,
                    password,
                    config.CRYPTOPAY_API_KEY)
            except cryptopay.InstantFiatError:
                self.message_user(
                    request,
                    'Merchant "{0}" - error.'.format(merchant.company_name),
                    messages.ERROR)
            else:
                self.message_user(
                    request,
                    'Merchant "{0}" - new password "{1}".'.format(
                        merchant.company_name, password),
                    messages.SUCCESS)

    reset_cryptopay_password.short_description = 'Reset CryptoPay password'


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

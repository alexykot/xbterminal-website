from decimal import Decimal
import json
import datetime
import re

from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse, Http404, StreamingHttpResponse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.views.generic import View
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.utils.decorators import method_decorator
from django.core.urlresolvers import resolve, reverse
from django.db.transaction import atomic
from django.utils.translation import ugettext as _

from formtools.wizard.views import CookieWizardView
from ipware.ip import get_real_ip

from api.utils import activation
from api.utils.urls import construct_absolute_url

from website import forms, models
from website.utils import email, kyc, reports


class LandingView(TemplateResponseMixin, View):
    """
    Landing page
    """
    template_name = "website/landing.html"

    def get(self, *args, **kwargs):
        return self.render_to_response({})


def android_app(request):
    return redirect('https://play.google.com/store/apps/details?id=ua.xbterminal.bitcoin')


def ios_app(request):
    return redirect('https://itunes.apple.com/us/app/xbterminal-bitcoin-pos/id909352652')


class ContactView(TemplateResponseMixin, View):
    """
    Contact form
    """
    template_name = "website/contact.html"

    def get(self, *args, **kwargs):
        form = forms.ContactForm(user_ip=get_real_ip(self.request))
        return self.render_to_response({'form': form})

    def post(self, *args, **kwargs):
        form = forms.ContactForm(self.request.POST,
                                 user_ip=get_real_ip(self.request))
        if form.is_valid():
            email.send_contact_email(form.cleaned_data)
            return self.render_to_response({})
        else:
            return self.render_to_response({'form': form})


class FeedbackView(TemplateResponseMixin, View):
    """
    Feedback form
    """
    template_name = "website/feedback.html"

    def get(self, *args, **kwargs):
        form = forms.FeedbackForm(user_ip=get_real_ip(self.request))
        return self.render_to_response({'form': form})

    def post(self, *args, **kwargs):
        form = forms.FeedbackForm(self.request.POST,
                                  user_ip=get_real_ip(self.request))
        if form.is_valid():
            email.send_feedback_email(form.cleaned_data)
            return self.render_to_response({})
        else:
            return self.render_to_response({'form': form})


class PrivacyPolicyView(TemplateResponseMixin, View):
    """
    Privacy policy page
    """
    template_name = "website/privacy.html"

    def get(self, *args, **kwargs):
        return self.render_to_response({})


class TermsConditionsView(TemplateResponseMixin, View):
    """
    Terms & Conditions page
    """
    template_name = "website/tc.html"

    def get(self, *args, **kwargs):
        return self.render_to_response({})


class TeamView(TemplateResponseMixin, View):
    """
    Team page
    """
    template_name = "website/team.html"

    def get(self, *args, **kwargs):
        return self.render_to_response({})


class LoginView(ContextMixin, TemplateResponseMixin, View):
    """
    Login page
    """
    template_name = "website/login.html"

    def get_context_data(self, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        context['next'] = self.request.POST.get(
            'next', self.request.GET.get('next', ''))
        return context

    def _redirect_after_login(self, user):
        if user.role == 'administrator':
            url = reverse('admin:index')
        elif user.role == 'merchant':
            url = reverse('website:devices')
        elif user.role == 'controller':
            url = reverse('website:merchant_list')
        else:
            url = reverse('website:landing')
        return redirect(url)

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            return self._redirect_after_login(self.request.user)
        context = self.get_context_data(**kwargs)
        context['form'] = forms.AuthenticationForm
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.AuthenticationForm(self.request, data=self.request.POST)
        if form.is_valid():
            user = form.get_user()
            login(self.request, user)
            return self._redirect_after_login(user)
        context['form'] = form
        return self.render_to_response(context)


class LogoutView(View):
    """
    Logout
    """
    def get(self, *args, **kwargs):
        logout(self.request)
        return redirect(reverse('website:landing'))


class ResetPasswordView(TemplateResponseMixin, View):
    """
    Reset password page
    """
    template_name = "website/reset_password.html"

    def get(self, *args, **kwargs):
        form = forms.ResetPasswordForm()
        return self.render_to_response({'form': form})

    def post(self, *args, **kwargs):
        form = forms.ResetPasswordForm(self.request.POST)
        if form.is_valid():
            form.set_new_password()
            return self.render_to_response({})
        else:
            return self.render_to_response({'form': form})


class RegistrationView(TemplateResponseMixin, View):
    """
    Registration page
    """
    template_name = "website/registration.html"

    def get(self, *args, **kwargs):
        if hasattr(self.request.user, 'merchant'):
            return redirect(reverse('website:devices'))
        form = forms.MerchantRegistrationForm()
        return self.render_to_response({'form': form})

    def post(self, *args, **kwags):
        form = forms.MerchantRegistrationForm(self.request.POST)
        if not form.is_valid():
            return self.render_to_response({'form': form})
        merchant = form.save()
        email.send_registration_info(merchant)
        login(self.request, merchant.user)
        return redirect(reverse('website:devices'))


class ActivationWizard(CookieWizardView):
    """
    Activate device and login
    """
    template_name = 'website/activation.html'
    form_list = [
        forms.DeviceActivationForm,
        forms.LoginMethodForm,
        forms.AuthenticationForm,
        forms.MerchantRegistrationForm,
    ]

    def show_login_form_condition(self):
        data = self.get_cleaned_data_for_step('1') or {}
        return data.get('method') == 'login'

    def show_registration_form_condition(self):
        data = self.get_cleaned_data_for_step('1') or {}
        return data.get('method') == 'register'

    condition_dict = {
        '2': show_login_form_condition,
        '3': show_registration_form_condition,
    }

    def dispatch(self, *args, **kwargs):
        if get_current_merchant(self.request):
            return redirect(reverse('website:activate_device'))
        return super(ActivationWizard, self).dispatch(*args, **kwargs)

    @atomic
    def done(self, form_list, **kwargs):
        # Get device
        device = form_list[0].device
        # Get merchant
        if self.show_login_form_condition():
            merchant = form_list[2].get_user().merchant
        elif self.show_registration_form_condition():
            merchant = form_list[2].save()
            email.send_registration_info(merchant)
        # Start activation
        activation.start(device, merchant)
        # Login & redirect
        login(self.request, merchant.user)
        return redirect(reverse('website:device_activation',
                                kwargs={'device_key': device.key}))


def get_current_merchant(request):
    if not hasattr(request.user, 'merchant'):
        return None
    return request.user.merchant


class MerchantCabinetView(ContextMixin, View):
    """
    Base class for merchant cabinet views
    """

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        self.merchant = get_current_merchant(request)
        if not self.merchant:
            raise Http404
        return super(MerchantCabinetView,
                     self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(MerchantCabinetView,
                        self).get_context_data(**kwargs)
        context['cabinet_page'] = resolve(self.request.path_info).url_name
        context['merchant'] = self.merchant
        return context


class DeviceListView(TemplateResponseMixin, MerchantCabinetView):
    """
    Device list page
    """
    template_name = 'cabinet/merchant/device_list.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['devices'] = self.merchant.device_set.order_by('-id')
        return self.render_to_response(context)


class ActivationView(MerchantCabinetView):

    def dispatch(self, request, *args, **kwargs):
        self.merchant = get_current_merchant(request)
        if not self.merchant:
            try:
                self.merchant = models.MerchantAccount.objects.get(
                    activation_code__iexact=self.kwargs.get('merchant_code'))
            except models.MerchantAccount.DoesNotExist:
                raise Http404
        return super(MerchantCabinetView, self).dispatch(request, *args, **kwargs)


class ActivateDeviceView(TemplateResponseMixin, ActivationView):

    template_name = 'cabinet/merchant/activation.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.DeviceActivationForm()
        context['activation_url'] = construct_absolute_url(
            'website:activate_device_nologin',
            kwargs={'merchant_code': self.merchant.activation_code})
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        form = forms.DeviceActivationForm(self.request.POST)
        if form.is_valid():
            activation.start(form.device, self.merchant)
            if not self.request.user.is_authenticated():
                return redirect(reverse(
                    'website:device_activation_nologin',
                    kwargs={
                        'merchant_code': self.merchant.activation_code,
                        'device_key': form.device.key,
                    }))
            else:
                return redirect(reverse(
                    'website:device_activation',
                    kwargs={'device_key': form.device.key}))
        else:
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)


class DeviceActivationView(TemplateResponseMixin, ActivationView):

    template_name = 'cabinet/merchant/activation.html'

    def get(self, *args, **kwargs):
        try:
            device = self.merchant.device_set.get(
                key=self.kwargs.get('device_key'))
        except models.Device.DoesNotExist:
            raise Http404
        context = self.get_context_data(**kwargs)
        context['device'] = device
        return self.render_to_response(context)


class DeviceMixin(ContextMixin):
    """
    Adds device to the context
    """

    def get_context_data(self, **kwargs):
        context = super(DeviceMixin, self).get_context_data(**kwargs)
        device_key = self.kwargs.get('device_key')
        try:
            context['device'] = self.merchant.device_set.\
                filter(status__in=['active', 'suspended']).\
                get(key=device_key)
        except models.Device.DoesNotExist:
            raise Http404
        return context


class UpdateDeviceView(DeviceMixin,
                       TemplateResponseMixin,
                       MerchantCabinetView):
    """
    Update device
    """
    template_name = 'cabinet/merchant/device_form.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.DeviceForm(
            instance=context['device'],
            merchant=self.merchant)
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.DeviceForm(self.request.POST,
                                instance=context['device'],
                                merchant=self.merchant)
        if form.is_valid():
            device = form.save()
            return redirect(reverse('website:device',
                                    kwargs={'device_key': device.key}))
        else:
            context['form'] = form
            return self.render_to_response(context)


class DeviceStatusView(DeviceMixin,
                       TemplateResponseMixin,
                       MerchantCabinetView):
    """
    Suspend or activate device
    """
    template_name = 'cabinet/merchant/device_status.html'

    def get_context_data(self, **kwargs):
        context = super(DeviceStatusView, self).get_context_data(**kwargs)
        if context['device'].status not in ['active', 'suspended']:
            raise Http404
        return context

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        device = context['device']
        if device.status == 'active':
            device.suspend()
        elif device.status == 'suspended':
            device.activate()
        device.save()
        return redirect(reverse('website:devices'))


class UpdateProfileView(TemplateResponseMixin, MerchantCabinetView):
    """
    Update profile
    """
    template_name = 'cabinet/merchant/profile_form.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.ProfileForm(instance=self.merchant)
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.ProfileForm(self.request.POST,
                                 instance=self.merchant)
        if form.is_valid():
            form.save()
            return redirect(reverse('website:profile'))
        else:
            context['form'] = form
            return self.render_to_response(context)


class ChangePasswordView(TemplateResponseMixin, MerchantCabinetView):
    """
    Change password
    """
    template_name = 'cabinet/merchant/change_password.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = PasswordChangeForm(self.request.user)
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = PasswordChangeForm(self.request.user, self.request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse('website:profile'))
        else:
            context['form'] = form
            return self.render_to_response(context)


class VerificationView(TemplateResponseMixin, MerchantCabinetView):
    """
    Verification page
    """
    template_name = 'cabinet/merchant/verification.html'

    def get(self, *args, **kwargs):
        if not self.merchant.has_managed_cryptopay_profile:
            raise Http404
        context = self.get_context_data(**kwargs)
        if self.merchant.verification_status == 'unverified':
            # Prepare upload forms
            context['forms'] = []
            for document_type in kyc.REQUIRED_DOCUMENTS:
                form = forms.KYCDocumentUploadForm(
                    document_type=document_type,
                    instance=self.merchant.get_kyc_document(
                        document_type, 'uploaded'))
                context['forms'].append(form)
        else:
            # Prepare documents
            context['documents'] = []
            for document_type in kyc.REQUIRED_DOCUMENTS:
                context['documents'].append(
                    self.merchant.get_current_kyc_document(document_type))
        return self.render_to_response(context)

    @atomic
    def post(self, *args, **kwargs):
        if not self.merchant.has_managed_cryptopay_profile:
            raise Http404
        if self.merchant.verification_status != 'unverified':
            raise Http404
        uploaded = []
        for document_type in kyc.REQUIRED_DOCUMENTS:
            document = self.merchant.get_kyc_document(document_type, 'uploaded')
            if not document:
                # Not all required documents are uploaded
                data = {'error': _('Please, upload documents')}
                return HttpResponse(json.dumps(data),
                                    content_type='application/json')
            uploaded.append(document)
        kyc.upload_documents(self.merchant, uploaded)
        data = {'next': reverse('website:verification')}
        return HttpResponse(json.dumps(data),
                            content_type='application/json')


class VerificationFileView(View):
    """
    View, upload or delete files
    """

    def dispatch(self, *args, **kwargs):
        # Get merchant
        self.merchant = get_object_or_404(
            models.MerchantAccount,
            pk=self.kwargs.get('merchant_pk'))
        # Parse file name
        match = re.match(r"^(?P<type>[0-9])(__.+$|$)",
                         self.kwargs.get('name'))
        if not match:
            raise Http404
        self.document_type = int(match.group('type'))
        self.file_name = match.group(0)
        return super(VerificationFileView, self).dispatch(*args, **kwargs)

    def get(self, *args, **kwargs):
        if (
            get_current_merchant(self.request) != self.merchant and
            not self.request.user.is_staff
        ):
            raise Http404
        for document in self.merchant.kycdocument_set.all():
            if document.base_name == self.file_name:
                return StreamingHttpResponse(
                    document.file.read(),
                    content_type='image')
        raise Http404

    def post(self, *args, **kwargs):
        if (
            get_current_merchant(self.request) != self.merchant or
            self.merchant.verification_status != 'unverified'
        ):
            raise Http404
        form = forms.KYCDocumentUploadForm(self.request.POST,
                                           self.request.FILES)
        if form.is_valid():
            # Remove previously uploaded file
            try:
                self.merchant.get_kyc_document(
                    self.document_type, 'uploaded').delete()
            except AttributeError:
                pass
            instance = form.save(commit=False)
            instance.merchant = self.merchant
            instance.document_type = self.document_type
            instance.save()
            data = {'filename': instance.original_name}
        else:
            data = {'errors': form.errors}
        return HttpResponse(json.dumps(data),
                            content_type='application/json')

    def delete(self, *args, **kwargs):
        if (
            get_current_merchant(self.request) != self.merchant or
            self.merchant.verification_status != 'unverified'
        ):
            raise Http404
        document = self.merchant.get_kyc_document(
            self.document_type, 'uploaded')
        if not document:
            raise Http404
        document.delete()
        return HttpResponse(json.dumps({'deleted': True}),
                            content_type='application/json')


class AccountListView(TemplateResponseMixin, MerchantCabinetView):
    """
    Account list page
    """
    template_name = 'cabinet/merchant/account_list.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['accounts'] = self.merchant.account_set.all()
        return self.render_to_response(context)


class AccountMixin(ContextMixin):
    """
    Adds account to the context
    """
    def get_context_data(self, **kwargs):
        context = super(AccountMixin, self).get_context_data(**kwargs)
        currency_code = self.kwargs.get('currency_code', '').upper()
        try:
            context['account'] = self.merchant.account_set.\
                get(currency__name=currency_code)
        except models.Account.DoesNotExist:
            raise Http404
        return context


class EditAccountView(AccountMixin,
                      TemplateResponseMixin,
                      MerchantCabinetView):
    """
    Edit account
    """
    template_name = 'cabinet/merchant/account_form.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.AccountForm(instance=context['account'])
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.AccountForm(self.request.POST,
                                 instance=context['account'])
        if form.is_valid():
            account = form.save()
            if account.instantfiat:
                email.send_bank_account_info(account)
            return redirect(reverse('website:accounts'))
        else:
            context['form'] = form
            return self.render_to_response(context)


class TransactionListView(TemplateResponseMixin, MerchantCabinetView):
    """
    Base class
    """
    template_name = 'cabinet/merchant/transactions.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        device_or_account = (context.get('device') or context.get('account'))
        context['search_form'] = forms.TransactionSearchForm()
        context['range_beg'] = context['range_end'] = datetime.date.today()
        context['transactions'] = device_or_account.\
            get_transactions_by_date(context['range_beg'],
                                     context['range_end'])
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        device_or_account = context.get('device') or context.get('account')
        form = forms.TransactionSearchForm(self.request.POST)
        if form.is_valid():
            context['range_beg'] = form.cleaned_data['range_beg']
            context['range_end'] = form.cleaned_data['range_end']
            context['transactions'] = device_or_account.\
                get_transactions_by_date(context['range_beg'],
                                         context['range_end'])
        context['search_form'] = form
        return self.render_to_response(context)


class DeviceTransactionListView(DeviceMixin, TransactionListView):
    """
    List device transactions
    """
    pass


class AccountTransactionListView(AccountMixin, TransactionListView):
    """
    List account transactions
    """
    pass


class ReportView(MerchantCabinetView):
    """
    Base class
    """
    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.TransactionSearchForm(data=self.request.GET)
        if not form.is_valid():
            raise Http404
        device_or_account = context.get('device') or context.get('account')
        transactions = device_or_account.get_transactions_by_date(
            form.cleaned_data['range_beg'],
            form.cleaned_data['range_end'])
        content_disposition = 'attachment; filename="{0}"'.format(
            reports.get_report_filename(device_or_account))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = content_disposition
        reports.get_report_csv(transactions, response)
        return response


class DeviceReportView(DeviceMixin, ReportView):
    """
    Download CSV file with device transactions
    """
    pass


class AccountReportView(AccountMixin, ReportView):
    """
    Download CSV file with account transactions
    """
    pass


class AddFundsView(AccountMixin,
                   TemplateResponseMixin,
                   MerchantCabinetView):
    """
    Add funds to account
    """
    template_name = 'payment/payment.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['amount'] = Decimal('0.00')
        return self.render_to_response(context)


class WithdrawToBankAccountView(AccountMixin,
                                TemplateResponseMixin,
                                MerchantCabinetView):
    """
    Withdraw funds from instantfiat account
    """
    template_name = 'cabinet/merchant/withdrawal_form.html'

    def get_context_data(self, **kwargs):
        context = super(WithdrawToBankAccountView, self).\
            get_context_data(**kwargs)
        if not context['account'].instantfiat:
            raise Http404
        return context

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.WithdrawToBankAccountForm(
            account=context['account'])
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.WithdrawToBankAccountForm(
            self.request.POST,
            account=context['account'])
        if form.is_valid():
            email.send_withdrawal_request(context['account'],
                                          form.cleaned_data['amount'])
            return redirect(reverse('website:accounts'))
        else:
            context['form'] = form
            return self.render_to_response(context)


class ControllerCabinetView(ContextMixin, View):
    """
    Base class for controller cabinet views
    """

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not request.user.role == 'controller':
            raise Http404
        return super(ControllerCabinetView, self).dispatch(
            request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ControllerCabinetView,
                        self).get_context_data(**kwargs)
        context['cabinet_page'] = resolve(self.request.path_info).url_name
        return context


class MerchantListView(TemplateResponseMixin, ControllerCabinetView):
    """
    Merchant list page
    """
    template_name = 'cabinet/controller/merchant_list.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['merchants'] = models.MerchantAccount.objects.\
            annotate(device_count=Count('device'))
        return self.render_to_response(context)


class MerchantMixin(ContextMixin):

    def get_context_data(self, **kwargs):
        context = super(MerchantMixin, self).get_context_data(**kwargs)
        merchant_id = self.kwargs.get('pk')
        try:
            context['merchant'] = models.MerchantAccount.objects.\
                get(pk=merchant_id)
        except models.MerchantAccount.DoesNotExist:
            raise Http404
        return context


class MerchantInfoView(TemplateResponseMixin,
                       MerchantMixin,
                       ControllerCabinetView):
    """
    Merchant details page
    """
    template_name = 'cabinet/controller/merchant_info.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


class MerchantDeviceListView(TemplateResponseMixin,
                             MerchantMixin,
                             ControllerCabinetView):
    """
    Merchant's device list
    """
    template_name = 'cabinet/controller/device_list.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['devices'] = context['merchant'].device_set.all()
        return self.render_to_response(context)


class MerchantDeviceInfoView(TemplateResponseMixin,
                             MerchantMixin,
                             ControllerCabinetView):
    """
    Merchant's device info page
    """
    template_name = 'cabinet/controller/device_info.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        device_key = self.kwargs.get('device_key')
        try:
            context['device'] = context['merchant'].device_set.\
                get(key=device_key)
        except models.Device.DoesNotExist:
            raise Http404
        return self.render_to_response(context)

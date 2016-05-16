from decimal import Decimal
import json
import datetime
import re
import traceback

from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse, Http404, HttpResponseBadRequest, StreamingHttpResponse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.views.generic import View
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.utils.decorators import method_decorator
from django.core.urlresolvers import resolve, reverse
from django.db.models import Count, Sum, F
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import ugettext as _

from ipware.ip import get_real_ip

from api.utils import activation

from website import forms, models
from website.utils import reconciliation, email


class ServerErrorMiddleware(object):

    def process_exception(self, request, exception):
        if not isinstance(exception, Http404):
            email.send_error_message(tb=traceback.format_exc())
        return None


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

    def get(self, *args, **kwargs):
        if hasattr(self.request.user, 'merchant'):
            return redirect(reverse('website:devices'))
        context = self.get_context_data(**kwargs)
        context['form'] = forms.AuthenticationForm
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.AuthenticationForm(self.request, data=self.request.POST)
        if form.is_valid():
            login(self.request, form.get_user())
            return redirect(context['next'] or reverse('website:devices'))
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
        context = {
            'form': forms.MerchantRegistrationForm(),
        }
        return self.render_to_response(context)

    def post(self, *args, **kwags):
        form = forms.MerchantRegistrationForm(self.request.POST)
        if not form.is_valid():
            response = {
                'result': 'error',
                'errors': form.errors,
            }
            return HttpResponse(json.dumps(response),
                                content_type='application/json')
        merchant = form.save()
        email.send_registration_info(merchant)
        response = {
            'result': 'ok',
            'next': reverse('website:devices'),
        }
        login(self.request, merchant.user)
        return HttpResponse(json.dumps(response),
                            content_type='application/json')


class RegValidationView(View):
    """
    Helper view for server-side validation
    """
    def get(self, *args, **kwargs):
        field_name = self.request.GET.get('field_name')
        if field_name not in ['company_name', 'contact_email']:
            return HttpResponseBadRequest()
        kwargs = {field_name + '__iexact': self.request.GET.get('value', '')}
        try:
            models.MerchantAccount.objects.get(**kwargs)
        except models.MerchantAccount.DoesNotExist:
            response = {'is_valid': True}
        else:
            response = {'is_valid': False}
        return HttpResponse(json.dumps(response),
                            content_type='application/json')


def get_current_merchant(request):
    if not hasattr(request.user, 'merchant'):
        return None
    return request.user.merchant


class CabinetView(ContextMixin, View):
    """
    Base class for cabinet views
    """

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not get_current_merchant(request):
            raise Http404
        return super(CabinetView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(CabinetView, self).get_context_data(**kwargs)
        context['cabinet_page'] = resolve(self.request.path_info).url_name
        return context


class DeviceList(TemplateResponseMixin, CabinetView):
    """
    Device list page
    """
    template_name = "cabinet/device_list.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['devices'] = self.request.user.merchant.\
            device_set.order_by('-id')
        return self.render_to_response(context)


class CreateDeviceView(TemplateResponseMixin, CabinetView):
    """
    Create device page
    """
    template_name = "cabinet/device_form.html"

    def get(self, *args, **kwargs):
        device_types = dict(models.Device.DEVICE_TYPES)
        device_type = self.request.GET.get('device_type', 'hardware')
        if device_type not in device_types:
            return HttpResponseBadRequest('')
        count = self.request.user.merchant.device_set.count()
        context = self.get_context_data(**kwargs)
        context['form'] = forms.DeviceForm(
            merchant=self.request.user.merchant,
            initial={
                'device_type': device_type,
                'name': u'{0} #{1}'.format(device_types[device_type], count + 1),
            })
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        form = forms.DeviceForm(self.request.POST,
                                merchant=self.request.user.merchant)
        if form.is_valid():
            device = form.save()
            return redirect(reverse('website:device',
                                    kwargs={'device_key': device.key}))
        else:
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)


class ActivateDeviceView(TemplateResponseMixin, CabinetView):

    template_name = 'cabinet/activation.html'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.DeviceActivationForm()
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        form = forms.DeviceActivationForm(self.request.POST)
        if form.is_valid():
            activation.start(form.device,
                             self.request.user.merchant)
            return redirect(reverse('website:activation',
                                    kwargs={'device_key': form.device.key}))
        else:
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)


class ActivationView(TemplateResponseMixin, CabinetView):

    template_name = 'cabinet/activation.html'

    def get(self, *args, **kwargs):
        merchant = self.request.user.merchant
        try:
            device = merchant.device_set.get(
                key=self.kwargs.get('device_key'))
        except models.Device.DoesNotExist:
            raise Http404
        if device.status != 'activation':
            # Activation already finished
            return redirect(reverse('website:device',
                                    kwargs={'device_key': device.key}))
        context = self.get_context_data(**kwargs)
        context['device'] = device
        return self.render_to_response(context)


class DeviceMixin(ContextMixin):
    """
    Adds device to the context
    """

    def get_context_data(self, **kwargs):
        context = super(DeviceMixin, self).get_context_data(**kwargs)
        merchant = self.request.user.merchant
        device_key = self.kwargs.get('device_key')
        try:
            context['device'] = merchant.device_set.\
                filter(status__in=['active', 'suspended']).\
                get(key=device_key)
        except models.Device.DoesNotExist:
            raise Http404
        return context


class UpdateDeviceView(DeviceMixin, TemplateResponseMixin, CabinetView):
    """
    Update device
    """
    template_name = "cabinet/device_form.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.DeviceForm(
            instance=context['device'],
            merchant=self.request.user.merchant)
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.DeviceForm(self.request.POST,
                                instance=context['device'],
                                merchant=self.request.user.merchant)
        if form.is_valid():
            device = form.save()
            return redirect(reverse('website:device',
                                    kwargs={'device_key': device.key}))
        else:
            context['form'] = form
            return self.render_to_response(context)


class UpdateProfileView(TemplateResponseMixin, CabinetView):
    """
    Update profile
    """
    template_name = "cabinet/profile_form.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        merchant = self.request.user.merchant
        context['form'] = forms.ProfileForm(instance=merchant)
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.ProfileForm(self.request.POST,
                                 instance=self.request.user.merchant)
        if form.is_valid():
            form.save()
            return redirect(reverse('website:profile'))
        else:
            context['form'] = form
            return self.render_to_response(context)


class InstantFiatSettingsView(TemplateResponseMixin, CabinetView):

    template_name = 'cabinet/instantfiat_form.html'

    def get_context_data(self, **kwargs):
        context = super(InstantFiatSettingsView, self).get_context_data(**kwargs)
        if self.request.user.merchant.instantfiat_merchant_id:
            raise Http404
        return context

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.InstantFiatSettingsForm(
            instance=self.request.user.merchant)
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.InstantFiatSettingsForm(
            self.request.POST,
            instance=self.request.user.merchant)
        if form.is_valid():
            form.save()
            return redirect(reverse('website:accounts'))
        else:
            context['form'] = form
            return self.render_to_response(context)


class ChangePasswordView(TemplateResponseMixin, CabinetView):
    """
    Change password
    """
    template_name = "cabinet/change_password.html"

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


class VerificationView(TemplateResponseMixin, CabinetView):
    """
    Verification page
    """
    template_name = "cabinet/verification.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        merchant = self.request.user.merchant
        if merchant.verification_status == 'unverified':
            # Prepare upload forms
            context['forms'] = []
            required = [
                models.KYC_DOCUMENT_TYPES.ID_FRONT,
                models.KYC_DOCUMENT_TYPES.ADDRESS,
            ]
            for document_type in required:
                # Show upload forms only for unverified documents
                if not merchant.get_kyc_document(document_type, 'verified'):
                    form = forms.KYCDocumentUploadForm(
                        document_type=document_type,
                        instance=merchant.get_kyc_document(
                            document_type, 'uploaded'))
                    context['forms'].append(form)
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        merchant = self.request.user.merchant
        if merchant.verification_status != 'unverified':
            raise Http404
        # All unverified documents must be uploaded
        kyc_documents = []
        if not merchant.get_kyc_document(1, 'verified'):
            kyc_documents.append(merchant.get_kyc_document(1, 'uploaded'))
        if not merchant.get_kyc_document(2, 'verified'):
            kyc_documents.append(merchant.get_kyc_document(2, 'uploaded'))
        if all(kyc_documents):
            for document in kyc_documents:
                document.status = 'unverified'
                document.save()
            merchant.verification_status = 'pending'
            merchant.save()
            email.send_verification_info(merchant)
            data = {'next': reverse('website:verification')}
        else:
            data = {'error': _('Please, upload documents')}
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
        match = re.match(r"^(?P<type>[12])(__.+$|$)",
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
                    content_type='application/octet-stream')
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


class AccountListView(TemplateResponseMixin, CabinetView):
    """
    Account list page
    """
    template_name = "cabinet/account_list.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['accounts'] = self.request.user.merchant.account_set.all()
        context['can_edit_ift_settings'] = \
            not self.request.user.merchant.instantfiat_merchant_id
        return self.render_to_response(context)


class EditAccountView(TemplateResponseMixin, CabinetView):
    """
    Edit account
    """
    template_name = 'cabinet/account_form.html'

    def get_context_data(self, **kwargs):
        context = super(EditAccountView, self).get_context_data(**kwargs)
        try:
            context['account'] = self.request.user.merchant.account_set.\
                get(pk=self.kwargs.get('pk'))
        except models.Account.DoesNotExist:
            raise Http404
        return context

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.AccountForm(instance=context['account'])
        return self.render_to_response(context)

    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.AccountForm(self.request.POST,
                                 instance=context['account'])
        if form.is_valid():
            form.save()
            return redirect(reverse('website:accounts'))
        else:
            context['form'] = form
            return self.render_to_response(context)


class ReconciliationView(DeviceMixin, TemplateResponseMixin, CabinetView):
    """
    Reconciliation page
    """
    template_name = "cabinet/reconciliation.html"

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        context['form'] = forms.SendDailyReconciliationForm()
        context['daily_payments_info'] = context['device'].\
            get_payments().\
            extra({'date': "date(time_notified)"}).\
            values('date', 'fiat_currency').\
            annotate(
                count=Count('id'),
                btc_amount=Sum(
                    F('merchant_btc_amount') +
                    F('instantfiat_btc_amount') +
                    F('fee_btc_amount') +
                    F('tx_fee_btc_amount')),
                fiat_amount=Sum('fiat_amount'),
                instantfiat_fiat_amount=Sum('instantfiat_fiat_amount')).\
            order_by('-date')
        context['send_form'] = forms.SendReconciliationForm(
            initial={'email': self.request.user.merchant.contact_email})
        return self.render_to_response(context)


class ReconciliationTimeView(DeviceMixin, CabinetView):
    """
    Edit reconciliation schedule
    """
    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        # Add time
        form = forms.SendDailyReconciliationForm(self.request.POST)
        if form.is_valid():
            rectime = form.save(commit=False)
            context['device'].rectime_set.add(rectime)
            return redirect('website:reconciliation',
                            context['device'].key)
        else:
            return HttpResponse('')

    def delete(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        # Remove time
        try:
            context['device'].rectime_set.get(
                pk=self.kwargs.get('pk')).delete()
        except models.ReconciliationTime.DoesNotExist:
            raise Http404
        return HttpResponse('')


class ReportView(DeviceMixin, CabinetView):
    """
    Download csv report
    """

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        if year and month and day:
            try:
                date = datetime.date(int(year), int(month), int(day))
            except ValueError:
                raise Http404
            payment_orders = context['device'].get_payments_by_date(date)
            content_disposition = 'attachment; filename="{0}"'.format(
                reconciliation.get_report_filename(context['device'], date))
        else:
            payment_orders = context['device'].get_payments()
            content_disposition = 'attachment; filename="{0}"'.format(
                reconciliation.get_report_filename(context['device']))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = content_disposition
        reconciliation.get_report_csv(payment_orders, response)
        return response


class ReceiptsView(DeviceMixin, CabinetView):
    """
    Download receipts
    """
    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')
        day = self.kwargs.get('day')
        if year and month and day:
            try:
                date = datetime.date(int(year), int(month), int(day))
            except ValueError:
                raise Http404
            payment_orders = context['device'].get_payments_by_date(date)
            content_disposition = 'attachment; filename="{0}"'.format(
                reconciliation.get_receipts_archive_filename(context['device'], date))
        else:
            payment_orders = context['device'].get_payments()
            content_disposition = 'attachment; filename="{0}"'.format(
                reconciliation.get_receipts_archive_filename(context['device']))
        response = HttpResponse(content_type='application/x-zip-compressed')
        response['Content-Disposition'] = content_disposition
        reconciliation.get_receipts_archive(payment_orders, response)
        return response


class SendAllToEmailView(DeviceMixin, CabinetView):
    """
    Send reports and receipts to email
    """
    def post(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        form = forms.SendReconciliationForm(self.request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            date = form.cleaned_data['date']
            # Calculate datetime range
            now = timezone.localtime(timezone.now())
            rec_range_beg = timezone.make_aware(
                datetime.datetime.combine(date, datetime.time.min),
                timezone.get_current_timezone())
            if date < now.date():
                rec_range_end = timezone.make_aware(
                    datetime.datetime.combine(date, datetime.time.max),
                    timezone.get_current_timezone())
            else:
                rec_range_end = now
            reconciliation.send_reconciliation(
                email, context['device'],
                (rec_range_beg, rec_range_end))
            messages.success(self.request,
                             _('Email has been sent successfully.'))
        else:
            messages.error(self.request,
                           _('Error: Invalid email. Please, try again.'))
        return redirect('website:reconciliation', context['device'].key)


class PaymentView(TemplateResponseMixin, View):
    """
    Online POS (public view)
    """

    template_name = "payment/payment.html"

    def get(self, *args, **kwargs):
        device = get_object_or_404(
            models.Device,
            key=self.kwargs.get('device_key'),
            status='active')
        try:
            amount = Decimal(self.request.GET.get('amount', '0.00'))
        except ArithmeticError:
            return HttpResponseBadRequest('invalid amount')
        response = self.render_to_response({
            'device': device,
            'amount': amount.quantize(Decimal('0.00')),
        })
        response['X-Frame-Options'] = 'ALLOW-FROM *'
        return response

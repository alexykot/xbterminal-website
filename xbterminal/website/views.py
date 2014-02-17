import json

from django.shortcuts import render
from django.http import HttpResponse

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.views.generic import UpdateView, ListView
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib import messages

from website.models import Device
from website.forms import ContactForm, MerchantRegistrationForm, ProfileForm, DeviceForm,\
    SendReconciliationForm, SendDailyReconciliationForm
from website.utils import send_reconciliation, get_transaction_csv


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            mail_text = render_to_string('website/email/contact.txt', form.cleaned_data)

            send_mail(
                "message from xbterminal.com",
                mail_text,
                settings.DEFAULT_FROM_EMAIL,
                settings.CONTACT_EMAIL_RECIPIENTS,
                fail_silently=False
            )
            return HttpResponse(json.dumps({'result': 'ok'}), content_type='application/json')
        else:
            to_response = {
                'result': 'error',
                'errors': form.errors
            }
            return HttpResponse(json.dumps(to_response), content_type='application/json')
    else:
        form = ContactForm()
    return render(request, 'website/contact.html', {'form': form})


def landing(request):
    return render(request, 'website/landing.html', {})


@xframe_options_exempt
def landing_faq(request):
    return render(request, 'website/faq.html', {})


def merchant(request):
    if request.method == 'POST':
        form = MerchantRegistrationForm(request.POST)
        if form.is_valid():
            UserModel = get_user_model()
            password = UserModel.objects.make_random_password()
            email = form.data['contact_email']
            user = UserModel.objects.create_user(email, email, password)

            merchant = form.save(commit=False)
            merchant.user = user
            merchant.save()

            mail_text = render_to_string('website/email/registration.txt',
                                         {'email': email, 'password': password})
            send_mail(
                "registration on xbterminal.com",
                mail_text,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False
            )

            to_response = {
                'result': 'ok'
            }
        else:
            to_response = {
                'result': 'error',
                'errors': form.errors
            }
        return HttpResponse(json.dumps(to_response), content_type='application/json')
    else:
        form = MerchantRegistrationForm()

    return render(request, 'website/merchant.html', {'form': form})


class ProfileView(UpdateView):
    form_class = ProfileForm
    template_name = 'cabinet/profile_form.html'
    success_url = reverse_lazy('website:profile')

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ProfileView, self).dispatch(*args, **kwargs)

    def get_object(self):
        user = self.request.user
        if not hasattr(user, 'merchant'):
            raise Http404
        return user.merchant


def get_device(merchant, number):
    if number is not None:
        try:
            number = int(number) - 1
            device = merchant.device_set.all()[number]
        except IndexError:
            raise Http404
    else:
        device = None

    return device


class DeviceView(UpdateView):
    form_class = DeviceForm
    template_name = 'cabinet/device_form.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(DeviceView, self).dispatch(*args, **kwargs)

    def get_object(self):
        user = self.request.user
        if not hasattr(user, 'merchant'):
            raise Http404

        number = self.kwargs.get('number')
        device = get_device(user.merchant, number)

        return device

    def form_valid(self, form):
        device = form.save(commit=False)
        device.merchant = self.request.user.merchant
        device.save()
        self.object = device
        return super(DeviceView, self).form_valid(form)

    def get_success_url(self):
        return reverse('website:devices')

    def get_context_data(self, **kwargs):
        kwargs['current_device'] = self.object
        return super(DeviceView, self).get_context_data(**kwargs)


class DeviceList(ListView):
    model = Device
    template_name = 'cabinet/device_list.html'
    context_object_name = 'devices'

    def get_queryset(self):
        return self.request.user.merchant.device_set.all()


def reconciliation(request, number):
    user = request.user
    if not hasattr(user, 'merchant'):
        raise Http404

    device = get_device(user.merchant, number)

    is_post = request.method == 'POST'
    if 'reset' in request.POST:
        device.email = device.time = None
        device.save()

        is_post = False

    form = SendDailyReconciliationForm(
        request.POST if is_post else None,
        instance=device
    )

    if form.is_valid():
        form.save()
        form = SendDailyReconciliationForm(instance=device)

    return render(request, 'cabinet/reconciliation.html', {'form': form, 'device': device})


def transaction_csv(request, number):
    user = request.user
    if not hasattr(user, 'merchant'):
        raise Http404

    device = get_device(user.merchant, number)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s device transactions.csv"' % device.name

    get_transaction_csv(device.transaction_set.all(), response)
    return response

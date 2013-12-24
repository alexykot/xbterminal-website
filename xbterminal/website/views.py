import json

from django.shortcuts import render
from django.http import HttpResponse

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.views.generic import UpdateView
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import Http404
from django.views.decorators.clickjacking import xframe_options_exempt

from website.forms import ContactForm, MerchantRegistrationForm, ProfileForm, DeviceForm


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
    template_name = 'website/profile_form.html'
    success_url = reverse_lazy('website:profile')

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ProfileView, self).dispatch(*args, **kwargs)

    def get_object(self):
        user = self.request.user
        if not hasattr(user, 'merchant'):
            raise Http404
        return user.merchant


class DeviceView(UpdateView):
    form_class = DeviceForm
    template_name = 'website/device_form.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(DeviceView, self).dispatch(*args, **kwargs)

    def get_object(self):
        user = self.request.user
        if not hasattr(user, 'merchant'):
            raise Http404

        number = self.kwargs.get('number')

        if number is not None:
            try:
                number = int(number) - 1
                device = user.merchant.device_set.all()[number]
            except IndexError:
                raise Http404
        else:
            device = None

        return device

    def form_valid(self, form):
        device = form.save(commit=False)
        device.merchant = self.request.user.merchant
        device.save()
        self.object = device
        return super(DeviceView, self).form_valid(form)

    def get_success_url(self):
        devices = list(self.request.user.merchant.device_set.all())
        device = self.object
        number = devices.index(device) + 1
        return reverse('website:device', kwargs={'number': number})

    def get_context_data(self, **kwargs):
        kwargs['current_device'] = self.object
        return super(DeviceView, self).get_context_data(**kwargs)

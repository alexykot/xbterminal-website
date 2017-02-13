from decimal import Decimal
import json
from mock import patch

from django.core.urlresolvers import reverse
from django.conf import settings
from django.test import TestCase
from django.core import mail
from django.core.cache import cache
from django.utils import timezone

from website.models import (
    MerchantAccount,
    Device,
    INSTANTFIAT_PROVIDERS,
    KYC_DOCUMENT_TYPES)
from website.tests.factories import (
    create_image,
    UserFactory,
    MerchantAccountFactory,
    KYCDocumentFactory,
    AccountFactory,
    TransactionFactory,
    DeviceFactory)
from operations.tests.factories import PaymentOrderFactory


class LandingViewTestCase(TestCase):

    def test_get(self):
        url = reverse('website:landing')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/landing.html')
        # Test website.context_processors.debug
        self.assertFalse(response.context['DEBUG'])


class ContactViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:contact')

    @patch('website.views.get_real_ip')
    def test_get_first(self, get_ip_mock):
        get_ip_mock.return_value = '10.123.45.1'
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/contact.html')
        form = response.context['form']
        self.assertNotIn('captcha', form.fields)

    @patch('website.views.get_real_ip')
    def test_get_captcha(self, get_ip_mock):
        get_ip_mock.return_value = '10.123.45.2'
        cache.set('form-contact-10.123.45.2', 3, timeout=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('captcha', form.fields)

    @patch('website.views.get_real_ip')
    def test_post(self, get_ip_mock):
        get_ip_mock.return_value = '10.123.45.3'
        form_data = {
            'email': 'test@example.net',
            'name': 'Test',
            'message': 'Test message',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])


class FeedbackViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:feedback')

    @patch('website.views.get_real_ip')
    def test_get_first(self, get_ip_mock):
        get_ip_mock.return_value = '10.123.45.1'
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/feedback.html')
        form = response.context['form']
        self.assertNotIn('captcha', form.fields)

    @patch('website.views.get_real_ip')
    def test_get_captcha(self, get_ip_mock):
        get_ip_mock.return_value = '10.123.45.2'
        cache.set('form-feedback-10.123.45.2', 3, timeout=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertIn('captcha', form.fields)

    @patch('website.views.get_real_ip')
    def test_post(self, get_ip_mock):
        get_ip_mock.return_value = '10.123.45.3'
        form_data = {
            'email': 'test@example.net',
            'message': 'Test message',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])


class LoginViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:login')

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/login.html')

    def test_get_merchant_logged_in(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertRedirects(
            response, reverse('website:devices'), status_code=302)

    def test_post_merchant(self):
        merchant = MerchantAccountFactory.create()
        form_data = {
            'username': merchant.user.email,
            'password': 'password',
        }
        response = self.client.post(self.url, form_data)
        self.assertRedirects(
            response, reverse('website:devices'), status_code=302)

    def test_post_administrator(self):
        user = UserFactory.create(is_staff=True)
        form_data = {
            'username': user.email,
            'password': 'password',
        }
        response = self.client.post(self.url, form_data)
        self.assertRedirects(
            response, reverse('admin:index'), status_code=302)


class RegistrationViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:registration')

    def test_get_default(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/registration.html')

    @patch('website.forms.cryptopay.create_merchant')
    def test_post(self, cryptopay_mock):
        cryptopay_mock.return_value = 'merchant_id'
        form_data = {
            'company_name': 'Test Company 1',
            'business_address': 'Test Address',
            'town': 'Test Town',
            'country': 'GB',
            'post_code': '123456',
            'contact_first_name': 'Test',
            'contact_last_name': 'Test',
            'contact_email': 'test1@example.net',
            'contact_phone': '+123456789',
            'terms': 'on',
        }
        response = self.client.post(self.url, data=form_data)
        self.assertEqual(response.status_code, 302)

        merchant = MerchantAccount.objects.get(
            company_name=form_data['company_name'])
        self.assertEqual(merchant.company_name, form_data['company_name'])
        self.assertEqual(merchant.user.email,
                         form_data['contact_email'])
        self.assertEqual(merchant.device_set.count(), 0)

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to[0],
                         form_data['contact_email'])
        self.assertEqual(mail.outbox[1].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])

    def test_post_errors(self):
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/registration.html')
        self.assertIn('company_name', response.context['form'].errors)


class ActivationWizardTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:activation_wizard')

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/activation.html')

    def test_redirect(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    @patch('api.utils.activation.rq_helpers')
    def test_login(self, rq_helpers_mock):
        merchant = MerchantAccountFactory.create()
        account_btc = AccountFactory.create(merchant=merchant)
        device = DeviceFactory.create(status='registered')
        form_data_0 = {
            'activation_wizard-current_step': '0',
            '0-activation_code': device.activation_code,
        }
        form_data_1 = {
            'activation_wizard-current_step': '1',
            '1-method': 'login',
        }
        form_data_2 = {
            'activation_wizard-current_step': '2',
            '2-username': merchant.user.email,
            '2-password': 'password',
        }
        response = self.client.post(self.url,
                                    form_data_0,
                                    format='multipart')
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url,
                                    form_data_1,
                                    format='multipart')
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url,
                                    form_data_2,
                                    format='multipart')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(rq_helpers_mock.run_task.called)
        self.assertTrue(rq_helpers_mock.run_periodic_task.called)
        self.assertEqual(len(mail.outbox), 0)
        device = Device.objects.get(pk=device.pk)
        self.assertEqual(device.merchant.pk, merchant.pk)
        self.assertEqual(device.status, 'activation_in_progress')
        self.assertEqual(device.account.pk, account_btc.pk)

    @patch('api.utils.activation.rq_helpers')
    @patch('website.forms.cryptopay.create_merchant')
    def test_register(self, cryptopay_mock, rq_helpers_mock):
        device = DeviceFactory.create(status='registered')
        cryptopay_mock.return_value = 'merchant_id'
        form_data_0 = {
            'activation_wizard-current_step': '0',
            '0-activation_code': device.activation_code,
        }
        form_data_1 = {
            'activation_wizard-current_step': '1',
            '1-method': 'register',
        }
        form_data_3 = {
            'activation_wizard-current_step': '3',
            '3-company_name': 'Test Company',
            '3-business_address': 'Test Address',
            '3-town': 'Test Town',
            '3-country': 'GB',
            '3-post_code': '123456',
            '3-contact_first_name': 'Test',
            '3-contact_last_name': 'Test',
            '3-contact_email': 'test@example.net',
            '3-contact_phone': '+123456789',
            '3-terms': 'on',
        }
        response = self.client.post(self.url,
                                    form_data_0,
                                    format='multipart')
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url,
                                    form_data_1,
                                    format='multipart')
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.url,
                                    form_data_3,
                                    format='multipart')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(rq_helpers_mock.run_task.called)
        self.assertTrue(rq_helpers_mock.run_periodic_task.called)
        device = Device.objects.get(pk=device.pk)
        self.assertIsNotNone(device.merchant)
        self.assertEqual(device.status, 'activation_in_progress')
        self.assertEqual(device.account.currency.name, 'BTC')
        merchant = device.merchant
        self.assertEqual(merchant.device_set.count(), 1)
        self.assertEqual(merchant.instantfiat_merchant_id,
                         'merchant_id')
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to[0],
                         form_data_3['3-contact_email'])
        self.assertEqual(mail.outbox[1].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])


class DeviceListViewTestCase(TestCase):

    def test_get(self):
        merchant = MerchantAccountFactory.create()
        account = AccountFactory.create(merchant=merchant)
        device_1, device_2 = DeviceFactory.create_batch(
            2, merchant=merchant, account=account)
        device_2.suspend()
        device_2.save()
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:devices')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/device_list.html')
        devices = response.context['devices']
        self.assertIn(device_1, devices)
        self.assertIn(device_2, devices)


class UpdateDeviceView(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_get_active(self):
        device = DeviceFactory.create(merchant=self.merchant)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:device',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/device_form.html')

    def test_get_activation(self):
        device = DeviceFactory.create(merchant=self.merchant,
                                      status='activation_in_progress')
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:device',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_get_suspended(self):
        device = DeviceFactory.create(merchant=self.merchant,
                                      status='suspended')
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:device',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/device_form.html')


class ActivateDeviceViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:activate_device')

    def test_get(self):
        merchant = MerchantAccountFactory.create()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/activation.html')

    @patch('api.utils.activation.rq_helpers.run_task')
    @patch('api.utils.activation.rq_helpers.run_periodic_task')
    def test_post_valid_code(self, run_periodic_mock, run_mock):
        merchant = MerchantAccountFactory.create()
        account = AccountFactory.create(merchant=merchant)
        self.assertEqual(merchant.device_set.count(), 0)
        self.client.login(username=merchant.user.email,
                          password='password')

        device = DeviceFactory.create(status='registered')
        form_data = {
            'activation_code': device.activation_code,
        }
        response = self.client.post(self.url, form_data, follow=True)
        self.assertTrue(run_mock.called)
        self.assertEqual(run_mock.call_args[1]['queue'], 'low')
        self.assertTrue(run_periodic_mock.called)
        expected_url = reverse('website:device_activation',
                               kwargs={'device_key': device.key})
        self.assertRedirects(response, expected_url)
        self.assertEqual(merchant.device_set.count(), 1)
        active_device = merchant.device_set.first()
        self.assertEqual(active_device.status, 'activation_in_progress')
        self.assertEqual(active_device.account.pk, account.pk)

    def test_post_error(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')

        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/activation.html')
        self.assertIn('activation_code',
                      response.context['form'].errors)


class DeviceActivationViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_get(self):
        device = DeviceFactory.create(merchant=self.merchant,
                                      status='activation_in_progress')
        url = reverse('website:device_activation',
                      kwargs={'device_key': device.key})
        self.client.login(username=self.merchant.user.email,
                          password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/activation.html')
        self.assertEqual(response.context['device'].pk,
                         device.pk)

    def test_already_active(self):
        device = DeviceFactory.create(merchant=self.merchant,
                                      status='active')
        url = reverse('website:device_activation',
                      kwargs={'device_key': device.key})
        self.client.login(username=self.merchant.user.email,
                          password='password')
        response = self.client.get(url)
        expected_url = reverse('website:device',
                               kwargs={'device_key': device.key})
        self.assertRedirects(response, expected_url)


class UpdateProfileViewTestCase(TestCase):

    def test_get(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/profile_form.html')
        self.assertEqual(response.context['form'].instance.pk,
                         merchant.pk)

    def test_post(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:profile')
        form_data = {
            'company_name': 'Test Company',
            'business_address': 'Test Address',
            'town': 'Test Town',
            'country': 'GB',
            'post_code': '123456',
            'contact_first_name': 'Test',
            'contact_last_name': 'Test',
            'contact_email': 'test@example.net',
            'contact_phone': '+123456789',
        }
        response = self.client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)


class ResetPasswordViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:reset_password')

    def test_get(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/reset_password.html')

    def test_post(self):
        merchant = MerchantAccountFactory.create()
        self.assertTrue(merchant.user.check_password('password'))
        form_data = {'email': merchant.user.email}
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], merchant.user.email)
        merchant_updated = MerchantAccount.objects.get(pk=merchant.pk)
        self.assertFalse(merchant_updated.user.check_password('password'))


class ChangePasswordViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:change_password')

    def test_get(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/change_password.html')

    def test_post(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        form_data = {
            'old_password': 'password',
            'new_password1': 'xxx',
            'new_password2': 'xxx',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)
        merchant_updated = MerchantAccount.objects.get(pk=merchant.pk)
        self.assertTrue(merchant_updated.user.check_password('xxx'))


class VerificationViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:verification')

    def test_no_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_get_no_managed_cryptopay_profile(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_get_unverified(self):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='test')
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/verification.html')
        self.assertEqual(len(response.context['forms']), 3)
        (form_1, form_2, form_3) = response.context['forms']
        self.assertEqual(form_1.document_type, KYC_DOCUMENT_TYPES.ID_FRONT)
        self.assertIsNone(form_1.instance.pk)
        self.assertEqual(form_2.document_type, KYC_DOCUMENT_TYPES.ID_BACK)
        self.assertIsNone(form_2.instance.pk)
        self.assertEqual(form_3.document_type, KYC_DOCUMENT_TYPES.ADDRESS)
        self.assertIsNone(form_3.instance.pk)

    def test_get_unverified_already_uploaded(self):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='test')
        doc_id = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_FRONT,
            status='uploaded')
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(len(response.context['forms']), 3)
        form = response.context['forms'][0]
        self.assertEqual(form.document_type, KYC_DOCUMENT_TYPES.ID_FRONT)
        self.assertEqual(form.instance.pk, doc_id.pk)

    def test_get_verification_pending(self):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='test',
            verification_status='pending')
        document_1 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_FRONT,
            status='unverified')
        document_2 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_BACK,
            status='unverified')
        document_3 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ADDRESS,
            status='unverified')
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/verification.html')
        self.assertNotIn('forms', response.context)
        self.assertEqual(len(response.context['documents']), 3)
        self.assertEqual(response.context['documents'][0].pk,
                         document_1.pk)
        self.assertEqual(response.context['documents'][1].pk,
                         document_2.pk)
        self.assertEqual(response.context['documents'][2].pk,
                         document_3.pk)

    @patch('website.utils.kyc.cryptopay.upload_documents')
    def test_post(self, upload_mock):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='xxx')
        upload_mock.return_value = 'x1z2b4'
        document_1 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_FRONT)
        document_2 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_BACK)
        document_3 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ADDRESS)
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])
        data = json.loads(response.content)
        self.assertIn('next', data)
        merchant.refresh_from_db()
        self.assertEqual(merchant.verification_status, 'pending')
        document_1.refresh_from_db()
        document_2.refresh_from_db()
        document_3.refresh_from_db()
        self.assertEqual(document_1.status, 'unverified')
        self.assertEqual(document_1.instantfiat_document_id, 'x1z2b4')
        self.assertEqual(document_2.status, 'unverified')
        self.assertEqual(document_2.instantfiat_document_id, 'x1z2b4')
        self.assertEqual(document_3.status, 'unverified')
        self.assertEqual(document_3.instantfiat_document_id, 'x1z2b4')

    def test_post_not_uploaded(self):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='test')
        doc_id = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_FRONT)
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('error', data)
        merchant.refresh_from_db()
        self.assertEqual(merchant.verification_status, 'unverified')
        doc_id.refresh_from_db()
        self.assertEqual(doc_id.status, 'uploaded')


class VerificationFileViewTestCase(TestCase):

    def test_get_identity_doc(self):
        merchant = MerchantAccountFactory.create()
        KYCDocumentFactory.create(merchant=merchant)
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:verification_file', kwargs={
            'merchant_pk': merchant.pk,
            'name': '1__test.png',
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_upload_identity_doc(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:verification_file', kwargs={
            'merchant_pk': merchant.pk,
            'name': 1,
        })
        with create_image(100) as data:
            response = self.client.post(url, {'file': data},
                                        format='multipart')
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertIn('filename', data)
        self.assertEqual(merchant.kycdocument_set.count(), 1)
        doc = merchant.kycdocument_set.first()
        self.assertEqual(doc.status, 'uploaded')
        self.assertEqual(doc.document_type, KYC_DOCUMENT_TYPES.ID_FRONT)

    def test_delete_identity_doc(self):
        merchant = MerchantAccountFactory.create()
        KYCDocumentFactory.create(merchant=merchant)
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:verification_file', kwargs={
            'merchant_pk': merchant.pk,
            'name': '1__test.png',
        })
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['deleted'])


class AccountListViewTestCase(TestCase):

    def test_get(self):
        merchant = MerchantAccountFactory.create()
        account = AccountFactory.create(merchant=merchant)
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:accounts')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/account_list.html')
        self.assertEqual(response.context['accounts'].first().pk,
                         account.pk)


class EditAccountViewTestCase(TestCase):

    def test_get(self):
        account = AccountFactory.create(currency__name='BTC')
        self.client.login(username=account.merchant.user.email,
                          password='password')
        url = reverse('website:account',
                      kwargs={'currency_code': 'btc'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/account_form.html')
        self.assertEqual(response.context['account'].pk, account.pk)

    def test_get_account_not_found(self):
        merchant = MerchantAccountFactory.create()
        AccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:account',
                      kwargs={'currency_code': 'yzx'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_post_btc_account(self):
        account = AccountFactory.create()
        self.client.login(username=account.merchant.user.email,
                          password='password')
        url = reverse('website:account',
                      kwargs={'currency_code': 'btc'})
        form_data = {
            'max_payout': '0.05',
            'forward_address': '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE',
        }
        response = self.client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_post_usd_account(self):
        account = AccountFactory.create(instantfiat=True,
                                        currency__name='USD')
        self.client.login(username=account.merchant.user.email,
                          password='password')
        url = reverse('website:account',
                      kwargs={'currency_code': 'usd'})
        form_data = {
            'bank_account_name': 'Test',
            'bank_account_bic': 'DEUTDEFF000',
            'bank_account_iban': 'GB82WEST12345698765432',
        }
        response = self.client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])

    def test_post_errors(self):
        account = AccountFactory.create(instantfiat=True,
                                        currency__name='GBP')
        self.client.login(username=account.merchant.user.email,
                          password='password')
        url = reverse('website:account',
                      kwargs={'currency_code': 'gbp'})
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertEqual(len(mail.outbox), 0)


class DeviceTransactionListViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_get(self):
        device = DeviceFactory.create(merchant=self.merchant)
        orders = PaymentOrderFactory.create_batch(
            5,
            device=device,
            time_notified=timezone.now())
        for order in orders:
            TransactionFactory.create(
                payment=order,
                account=order.account,
                amount=order.merchant_btc_amount)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:device_transactions',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/transactions.html')
        # New
        self.assertIn('search_form', response.context)
        self.assertEqual(response.context['range_beg'],
                         response.context['range_end'])
        transactions = response.context['transactions']
        self.assertEqual(transactions.count(), len(orders))
        self.assertEqual(transactions[0].amount,
                         orders[0].merchant_btc_amount)

    def test_post(self):
        device = DeviceFactory.create(merchant=self.merchant)
        now = timezone.now()
        tx = TransactionFactory.create(
            payment=PaymentOrderFactory.create(device=device),
            account=device.account,
            created_at=now)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:device_transactions',
                      kwargs={'device_key': device.key})
        data = {
            'range_beg': now.strftime('%Y-%m-%d'),
            'range_end': now.strftime('%Y-%m-%d'),
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/transactions.html')
        self.assertIn('search_form', response.context)
        self.assertEqual(response.context['range_beg'], now.date())
        self.assertEqual(response.context['range_end'], now.date())
        transactions = response.context['transactions']
        self.assertEqual(transactions.count(), 1)
        self.assertEqual(transactions[0].pk, tx.pk)

    def test_post_error(self):
        device = DeviceFactory.create(merchant=self.merchant)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:device_transactions',
                      kwargs={'device_key': device.key})
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/transactions.html')
        self.assertIn('search_form', response.context)
        self.assertNotIn('range_beg', response.context)
        self.assertNotIn('range_end', response.context)
        self.assertNotIn('transactions', response.context)


class AccountTransactionListViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_get(self):
        account = AccountFactory.create(merchant=self.merchant)
        tx = TransactionFactory.create(account=account)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:account_transactions',
                      kwargs={'currency_code': 'btc'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/transactions.html')
        self.assertIn('search_form', response.context)
        self.assertEqual(response.context['range_beg'],
                         response.context['range_end'])
        transactions = response.context['transactions']
        self.assertEqual(transactions.count(), 1)
        self.assertEqual(transactions[0].pk, tx.pk)

    def test_post(self):
        account = AccountFactory.create(merchant=self.merchant)
        now = timezone.now()
        tx = TransactionFactory.create(account=account, created_at=now)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:account_transactions',
                      kwargs={'currency_code': 'btc'})
        data = {
            'range_beg': now.strftime('%Y-%m-%d'),
            'range_end': now.strftime('%Y-%m-%d'),
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/transactions.html')
        self.assertIn('search_form', response.context)
        self.assertEqual(response.context['range_beg'], now.date())
        self.assertEqual(response.context['range_end'], now.date())
        transactions = response.context['transactions']
        self.assertEqual(transactions.count(), 1)
        self.assertEqual(transactions[0].pk, tx.pk)


class DeviceReportViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        device = DeviceFactory.create(merchant=self.merchant)
        tx = TransactionFactory.create(
            payment=PaymentOrderFactory.create(device=device),
            account=device.account)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:device_report',
                      kwargs={'device_key': device.key})
        date_str = tx.created_at.strftime('%Y-%m-%d')
        url += '?range_beg={date}&range_end={date}'.format(date=date_str)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Content-Disposition'))

    def test_no_dates(self):
        device = DeviceFactory.create(merchant=self.merchant)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:device_report',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class AccountReportViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        account = AccountFactory.create(merchant=self.merchant)
        tx = TransactionFactory.create(account=account)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:account_report',
                      kwargs={'currency_code': 'btc'})
        date_str = tx.created_at.strftime('%Y-%m-%d')
        url += '?range_beg={date}&range_end={date}'.format(date=date_str)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Content-Disposition'))


class AddFundsViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        account = AccountFactory.create(merchant=self.merchant)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:account_add_funds',
                      kwargs={'currency_code': 'btc'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payment/payment.html')
        self.assertEqual(response.context['account'].pk, account.pk)

    def test_invalid_currency_code(self):
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:account_add_funds',
                      kwargs={'currency_code': 'xxx'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class WithdrawToBankAccountForm(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_get(self):
        account = AccountFactory.create(merchant=self.merchant,
                                        instantfiat=True,
                                        currency__name='GBP')
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:account_withdrawal',
                      kwargs={'currency_code': 'gbp'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/withdrawal_form.html')
        self.assertEqual(response.context['account'].pk, account.pk)
        self.assertEqual(response.context['form'].account.pk, account.pk)

    def test_get_btc(self):
        AccountFactory.create(merchant=self.merchant,
                              instantfiat=False,
                              currency__name='BTC')
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:account_withdrawal',
                      kwargs={'currency_code': 'btc'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_post(self):
        account = AccountFactory.create(merchant=self.merchant,
                                        instantfiat=True,
                                        currency__name='GBP')
        TransactionFactory.create(account=account, amount=Decimal('1.0'))
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:account_withdrawal',
                      kwargs={'currency_code': 'gbp'})
        data = {'amount': '0.5'}
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])

    def test_post_btc(self):
        AccountFactory.create(merchant=self.merchant,
                              instantfiat=False,
                              currency__name='BTC')
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:account_withdrawal',
                      kwargs={'currency_code': 'btc'})
        data = {'amount': '0.5'}
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 404)

    def test_post_invalid_amount(self):
        AccountFactory.create(merchant=self.merchant,
                              instantfiat=True,
                              currency__name='GBP')
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:account_withdrawal',
                      kwargs={'currency_code': 'gbp'})
        data = {'amount': '0.5'}
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/merchant/withdrawal_form.html')
        self.assertEqual(len(mail.outbox), 0)


class MerchantListViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:merchants')

    def test_get(self):
        user = UserFactory.create(groups__names=['controllers'])
        merchant = MerchantAccountFactory.create()
        self.client.login(username=user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'cabinet/controller/merchant_list.html')
        merchants = response.context['merchants']
        self.assertEqual(merchants.count(), 1)
        self.assertIn(merchant, merchants)

    def test_get_as_merchant(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

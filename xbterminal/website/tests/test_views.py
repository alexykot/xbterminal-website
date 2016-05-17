import json
from django.core.urlresolvers import reverse
from django.conf import settings
from django.test import TestCase
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from mock import patch

from website.models import (
    MerchantAccount,
    INSTANTFIAT_PROVIDERS,
    KYC_DOCUMENT_TYPES)
from website.tests.factories import (
    create_image,
    MerchantAccountFactory,
    KYCDocumentFactory,
    AccountFactory,
    DeviceFactory,
    ReconciliationTimeFactory)
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

    def test_get_merchant(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_post(self):
        merchant = MerchantAccountFactory.create()
        form_data = {
            'username': merchant.user.email,
            'password': 'password',
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 302)


class RegistrationViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:registration')

    def test_get_default(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'website/registration.html')

    @patch('website.forms.cryptopay.create_merchant')
    @patch('website.forms.create_managed_accounts')
    def test_post_default(self, create_acc_mock, cryptopay_mock):
        cryptopay_mock.return_value = ('merchant_id', 'g3h4j5')
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
        }
        response = self.client.post(self.url, data=form_data)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['result'], 'ok')

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
        self.assertTemplateUsed(response, 'cabinet/device_list.html')
        devices = response.context['devices']
        self.assertIn(device_1, devices)
        self.assertIn(device_2, devices)


class CreateDeviceViewTestCase(TestCase):

    def setUp(self):
        self.url = reverse('website:create_device')

    def test_get(self):
        merchant = MerchantAccountFactory.create()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.client.login(username=merchant.user.email,
                          password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cabinet/device_form.html')
        self.assertEqual(response.context['form'].initial['device_type'],
                         'hardware')

    def test_post(self):
        merchant = MerchantAccountFactory.create()
        account = AccountFactory.create(merchant=merchant,
                                        currency__name='GBP')
        self.client.login(username=merchant.user.email,
                          password='password')
        self.assertEqual(merchant.device_set.count(), 0)
        form_data = {
            'device_type': 'hardware',
            'name': 'Terminal',
            'account': account.pk,
        }
        response = self.client.post(self.url, form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(merchant.device_set.count(), 1)
        device = merchant.device_set.first()
        self.assertEqual(device.account.pk, account.pk)
        self.assertEqual(device.status, 'active')
        self.assertEqual(device.device_type, 'hardware')
        self.assertEqual(device.name, 'Terminal')


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
        self.assertTemplateUsed(response, 'cabinet/device_form.html')

    def test_get_activation(self):
        device = DeviceFactory.create(merchant=self.merchant,
                                      status='activation')
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
        self.assertTemplateUsed(response, 'cabinet/device_form.html')


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
        self.assertTemplateUsed(response, 'cabinet/activation.html')

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
        expected_url = reverse('website:activation',
                               kwargs={'device_key': device.key})
        self.assertRedirects(response, expected_url)
        self.assertEqual(merchant.device_set.count(), 1)
        active_device = merchant.device_set.first()
        self.assertEqual(active_device.status, 'activation')
        self.assertEqual(active_device.account.pk, account.pk)

    def test_post_error(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')

        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cabinet/activation.html')
        self.assertIn('activation_code',
                      response.context['form'].errors)


class ActivationViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_get(self):
        device = DeviceFactory.create(merchant=self.merchant,
                                      status='activation')
        url = reverse('website:activation',
                      kwargs={'device_key': device.key})
        self.client.login(username=self.merchant.user.email,
                          password='password')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cabinet/activation.html')
        self.assertEqual(response.context['device'].pk,
                         device.pk)

    def test_already_active(self):
        device = DeviceFactory.create(merchant=self.merchant,
                                      status='active')
        url = reverse('website:activation',
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
        self.assertTemplateUsed(response, 'cabinet/profile_form.html')
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


class InstantFiatSettingsViewTestCase(TestCase):

    def test_get(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:instantfiat')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cabinet/instantfiat_form.html')
        self.assertEqual(response.context['form'].instance.pk,
                         merchant.pk)

    def test_get_managed_profile(self):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='test-id',
            instantfiat_api_key='xxxyyyzzz')
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:instantfiat')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_post(self):
        merchant = MerchantAccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:instantfiat')
        form_data = {'instantfiat_api_key': 'xxx'}
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
        self.assertTemplateUsed(response, 'cabinet/change_password.html')

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
        self.assertTemplateUsed(response, 'cabinet/verification.html')
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
        self.assertTemplateUsed(response, 'cabinet/verification.html')
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
        self.assertTemplateUsed(response, 'cabinet/account_list.html')
        self.assertEqual(response.context['accounts'].first().pk,
                         account.pk)
        self.assertTrue(response.context['can_edit_ift_settings'])

    def test_get_managed_profile(self):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='test-id',
            instantfiat_api_key='xxxyyyzzz')
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:accounts')
        response = self.client.get(url)
        self.assertFalse(response.context['can_edit_ift_settings'])


class EditAccountViewTestCase(TestCase):

    def test_get(self):
        account = AccountFactory.create()
        self.client.login(username=account.merchant.user.email,
                          password='password')
        url = reverse('website:account', kwargs={'pk': account.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cabinet/account_form.html')
        self.assertEqual(response.context['account'].pk, account.pk)

    def test_get_account_not_found(self):
        merchant = MerchantAccountFactory.create()
        account = AccountFactory.create()
        self.client.login(username=merchant.user.email,
                          password='password')
        url = reverse('website:account', kwargs={'pk': account.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_post(self):
        account = AccountFactory.create()
        self.client.login(username=account.merchant.user.email,
                          password='password')
        url = reverse('website:account', kwargs={'pk': account.pk})
        form_data = {
            'forward_address': '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE',
        }
        response = self.client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)


class ReconciliationViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        device = DeviceFactory.create(merchant=self.merchant)
        orders = PaymentOrderFactory.create_batch(
            5,
            device=device,
            time_notified=timezone.now())
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:reconciliation',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cabinet/reconciliation.html')
        payments = response.context['daily_payments_info']
        self.assertEqual(payments[0]['count'], len(orders))
        self.assertEqual(payments[0]['btc_amount'],
                         sum(po.btc_amount for po in orders))
        self.assertEqual(payments[0]['fiat_amount'],
                         sum(po.fiat_amount for po in orders))
        self.assertEqual(payments[0]['instantfiat_fiat_amount'],
                         sum(po.instantfiat_fiat_amount for po in orders))


class ReconciliationTimeViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_post(self):
        device = DeviceFactory.create(merchant=self.merchant)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:reconciliation_time',
                      kwargs={'device_key': device.key, 'pk': 0})
        form_data = {
            'email': 'test@example.net',
            'time': '4:30 AM',
        }
        response = self.client.post(url, form_data)
        self.assertEqual(response.status_code, 302)
        rectime = device.rectime_set.first()
        self.assertEqual(rectime.email, form_data['email'])
        self.assertEqual(rectime.time.hour, 4)

    def test_delete(self):
        device = DeviceFactory.create(merchant=self.merchant)
        rectime = ReconciliationTimeFactory(device=device)
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:reconciliation_time',
                      kwargs={'device_key': device.key, 'pk': rectime.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(device.rectime_set.count(), 0)

        url = reverse('website:reconciliation_time',
                      kwargs={'device_key': device.key, 'pk': rectime.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)


class ReportViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        device = DeviceFactory.create(merchant=self.merchant)
        PaymentOrderFactory.create(
            device=device,
            incoming_tx_ids=['0' * 64],
            time_notified=timezone.now())
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:report',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Content-Disposition'))


class ReceiptsViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        device = DeviceFactory.create(merchant=self.merchant)
        PaymentOrderFactory.create(
            device=device,
            incoming_tx_ids=['0' * 64],
            time_notified=timezone.now())
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:receipts',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.has_header('Content-Disposition'))


class SendAllToEmailViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        device = DeviceFactory.create(merchant=self.merchant)
        payment_order = PaymentOrderFactory.create(
            device=device,
            incoming_tx_ids=['0' * 64],
            time_notified=timezone.now())
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:send_all_to_email',
                      kwargs={'device_key': device.key})
        form_data = {
            'email': 'test@example.net',
            'date': payment_order.time_notified.strftime('%Y-%m-%d'),
        }
        response = self.client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], form_data['email'])

    @patch('website.utils.email.create_html_message')
    def test_data(self, create_mock):
        device = DeviceFactory.create(merchant=self.merchant)
        orders = PaymentOrderFactory.create_batch(
            5,
            device=device,
            incoming_tx_ids=['0' * 64],
            time_notified=timezone.now())
        self.client.login(username=self.merchant.user.email,
                          password='password')
        url = reverse('website:send_all_to_email',
                      kwargs={'device_key': device.key})
        form_data = {
            'email': 'test@example.net',
            'date': orders[0].time_notified.strftime('%Y-%m-%d'),
        }
        self.client.post(url, data=form_data)
        self.assertTrue(create_mock.called)
        context = create_mock.call_args[0][2]
        self.assertEqual(context['device'].pk, device.pk)
        self.assertEqual(context['btc_amount'],
                         sum(po.btc_amount for po in orders))
        self.assertEqual(context['fiat_amount'],
                         sum(po.fiat_amount for po in orders))
        attachments = create_mock.call_args[1]['attachments']
        self.assertEqual(len(attachments), 2)
        self.assertEqual(attachments[0][2], 'text/csv')
        self.assertEqual(attachments[1][2], 'application/x-zip-compressed')


class PaymentViewTestCase(TestCase):

    def setUp(self):
        self.merchant = MerchantAccountFactory.create()

    def test_view(self):
        device = DeviceFactory.create(merchant=self.merchant)
        url = reverse('website:payment',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payment/payment.html')

    def test_activation(self):
        device = DeviceFactory.create(merchant=self.merchant,
                                      status='activation')
        url = reverse('website:payment',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_suspended(self):
        device = DeviceFactory.create(merchant=self.merchant,
                                      status='suspended')
        url = reverse('website:payment',
                      kwargs={'device_key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

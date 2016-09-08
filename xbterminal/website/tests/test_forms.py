# -*- coding: utf-8 -*-
from decimal import Decimal

from django.test import TestCase
from django.core import mail
from django.utils.datastructures import MultiValueDict
from mock import patch

from oauth2_provider.models import Application
from website.models import (
    MerchantAccount,
    INSTANTFIAT_PROVIDERS)
from website.forms import (
    MerchantRegistrationForm,
    ResetPasswordForm,
    ProfileForm,
    InstantFiatSettingsForm,
    KYCDocumentUploadForm,
    DeviceForm,
    DeviceActivationForm,
    AccountForm)
from website.tests.factories import (
    create_uploaded_image,
    CurrencyFactory,
    MerchantAccountFactory,
    AccountFactory,
    DeviceFactory)
from operations.exceptions import CryptoPayUserAlreadyExists


class MerchantRegistrationFormTestCase(TestCase):

    @patch('website.forms.cryptopay.create_merchant')
    @patch('website.utils.accounts.cryptopay.list_accounts')
    def test_valid_data(self, cp_list_mock, cp_create_mock):
        cp_create_mock.return_value = ('merchant_id', 'x1y2z3')
        cp_list_mock.return_value = [
            {'id': 'a1', 'currency': 'BTC'},
            {'id': 'a2', 'currency': 'GBP'},
            {'id': 'a3', 'currency': 'USD'},
            {'id': 'a4', 'currency': 'EUR'},
        ]
        form_data = {
            'company_name': 'Test Company',
            'business_address': 'Test Address',
            'town': 'Test Town',
            'country': 'GB',
            'post_code': '123456',
            'contact_first_name': u'Тест',
            'contact_last_name': u'Тест',
            'contact_email': 'test@example.net',
            'contact_phone': '+123456789',
        }
        form = MerchantRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        merchant = form.save()
        self.assertEqual(merchant.company_name, form_data['company_name'])
        self.assertEqual(merchant.contact_first_name,
                         form_data['contact_first_name'])
        self.assertEqual(merchant.contact_last_name,
                         form_data['contact_last_name'])
        self.assertEqual(merchant.user.email, form_data['contact_email'])
        self.assertEqual(merchant.language.code, 'en')
        self.assertEqual(merchant.currency.name, 'GBP')
        self.assertEqual(merchant.instantfiat_provider,
                         INSTANTFIAT_PROVIDERS.CRYPTOPAY)
        self.assertEqual(merchant.instantfiat_merchant_id, 'merchant_id')
        self.assertEqual(merchant.instantfiat_api_key, 'x1y2z3')
        # Oauth
        oauth_app = Application.objects.get(user=merchant.user)
        self.assertEqual(oauth_app.client_id, form_data['contact_email'])
        # Accounts
        self.assertEqual(merchant.account_set.count(), 5)
        account_btc_internal = merchant.account_set.get(
            currency__name='BTC', instantfiat=False)
        self.assertEqual(account_btc_internal.balance, 0)
        self.assertEqual(account_btc_internal.balance_max, 0)
        self.assertIsNone(account_btc_internal.instantfiat_account_id)
        account_btc_external = merchant.account_set.get(
            currency__name='BTC', instantfiat=True)
        self.assertEqual(account_btc_external.balance, 0)
        self.assertEqual(account_btc_external.balance_max, 0)
        self.assertEqual(account_btc_external.instantfiat_account_id, 'a1')
        # Email
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], form_data['contact_email'])

    @patch('website.forms.cryptopay.create_merchant')
    def test_cryptopay_user_alredy_exists(self, cryptopay_mock):
        cryptopay_mock.side_effect = CryptoPayUserAlreadyExists
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
        form = MerchantRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        merchant = form.save()
        self.assertEqual(merchant.account_set.count(), 1)
        self.assertEqual(merchant.account_set.first().currency.name, 'BTC')

    def test_required(self):
        form = MerchantRegistrationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('company_name', form.errors)
        self.assertIn('business_address', form.errors)
        self.assertIn('town', form.errors)
        self.assertIn('country', form.errors)
        self.assertIn('post_code', form.errors)
        self.assertIn('contact_first_name', form.errors)
        self.assertIn('contact_last_name', form.errors)
        self.assertIn('contact_email', form.errors)
        self.assertIn('contact_phone', form.errors)

    def test_invalid_names(self):
        form_data = {
            'company_name': 'Test Company',
            'business_address': 'Test Address',
            'town': 'Test Town',
            'country': 'GB',
            'post_code': '123456',
            'contact_first_name': 'User1',
            'contact_last_name': 'User.',
            'contact_email': 'test@example.net',
            'contact_phone': '+123456789',
        }
        form = MerchantRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['contact_first_name'][0],
            'Enter a valid name. This value may contain only letters.')
        self.assertEqual(
            form.errors['contact_last_name'][0],
            'Enter a valid name. This value may contain only letters.')

    @patch('website.forms.cryptopay.create_merchant')
    @patch('website.forms.create_managed_accounts')
    @patch('website.forms.send_registration_email')
    def test_send_email_error(self, send_mock, create_acc_mock, cp_create_mock):
        send_mock.side_effect = ValueError
        cp_create_mock.return_value = ('merchant_id', 'a1b2c3')
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
        form = MerchantRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        with self.assertRaises(ValueError):
            form.save()
        self.assertFalse(MerchantAccount.objects.filter(
            company_name=form_data['company_name']).exists())


class ResetPasswordFormTestCase(TestCase):

    def test_valid_data(self):
        merchant = MerchantAccountFactory.create()
        form_data = {'email': merchant.user.email}
        form = ResetPasswordForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form._user.pk, merchant.user.pk)
        form.set_new_password()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], merchant.user.email)

    def test_invalid_email(self):
        form_data = {'email': 'invalid@example.com'}
        form = ResetPasswordForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIsNone(form._user)


class ProfileFormTestCase(TestCase):

    def test_valid_data(self):
        merchant = MerchantAccountFactory.create()
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
        form = ProfileForm(data=form_data, instance=merchant)
        self.assertTrue(form.is_valid())
        merchant_updated = form.save()
        self.assertEqual(merchant_updated.pk, merchant.pk)
        self.assertEqual(merchant_updated.company_name,
                         form_data['company_name'])

    def test_no_instantfiat_api_key(self):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_api_key=None)
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
        form = ProfileForm(data=form_data, instance=merchant)
        self.assertTrue(form.is_valid())


class InstantFiatSettingsFormTestCase(TestCase):

    def test_valid_data(self):
        merchant = MerchantAccountFactory.create()
        form_data = {
            'instantfiat_api_key': 'test123456',
        }
        form = InstantFiatSettingsForm(data=form_data, instance=merchant)
        self.assertTrue(form.is_valid())
        merchant_updated = form.save()
        self.assertEqual(merchant_updated.pk, merchant.pk)
        self.assertEqual(merchant_updated.instantfiat_provider,
                         INSTANTFIAT_PROVIDERS.CRYPTOPAY)
        self.assertEqual(merchant_updated.instantfiat_api_key,
                         form_data['instantfiat_api_key'])

    def test_required(self):
        merchant = MerchantAccountFactory.create()
        form = InstantFiatSettingsForm(data={}, instance=merchant)
        self.assertFalse(form.is_valid())
        self.assertNotIn('instantfiat_provider', form.errors)
        self.assertIn('instantfiat_api_key', form.errors)


class KYCDocumentUploadFormTestCase(TestCase):

    def test_upload(self):
        files = MultiValueDict({'file': [create_uploaded_image(100)]})
        form = KYCDocumentUploadForm(data={}, files=files)
        self.assertIsNone(form.document_type)
        self.assertTrue(form.is_valid())
        document = form.save(commit=False)
        self.assertIsNotNone(document.file)


class DeviceFormTestCase(TestCase):

    def test_init(self):
        with self.assertRaises(KeyError):
            DeviceForm()

    def test_create_valid(self):
        merchant = MerchantAccountFactory.create()
        account = AccountFactory.create(merchant=merchant)
        form_data = {
            'device_type': 'mobile',
            'name': 'Mobile',
            'account': account.pk,
        }
        form = DeviceForm(data=form_data, merchant=merchant)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.device_type_verbose(), 'Mobile app')
        device = form.save()
        self.assertEqual(device.merchant.pk, merchant.pk)
        self.assertEqual(device.device_type, 'mobile')
        self.assertEqual(device.name, form_data['name'])
        self.assertEqual(device.account.pk, account.pk)
        self.assertEqual(device.status, 'active')

    def test_update_valid(self):
        device = DeviceFactory.create()
        form_data = {
            'device_type': 'hardware',
            'name': 'New Name',
            'account': device.account.pk,
        }
        form = DeviceForm(data=form_data,
                          merchant=device.merchant,
                          instance=device)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.device_type_verbose(), 'Terminal')
        device = form.save()
        self.assertEqual(device.device_type, 'hardware')
        self.assertEqual(device.name, form_data['name'])
        self.assertEqual(device.status, 'active')

    def test_required(self):
        merchant = MerchantAccountFactory.create()
        form = DeviceForm(data={}, merchant=merchant)
        self.assertFalse(form.is_valid())
        self.assertIn('device_type', form.errors)
        self.assertIn('name', form.errors)
        self.assertIn('account', form.errors)

    def test_invalid_account_currency(self):
        merchant = MerchantAccountFactory.create(currency__name='USD')
        account = AccountFactory.create(merchant=merchant,
                                        currency__name='EUR')
        form_data = {
            'device_type': 'hardware',
            'name': 'Terminal',
            'account': account.pk,
        }
        form = DeviceForm(data=form_data, merchant=merchant)
        self.assertFalse(form.is_valid())
        self.assertIn('account', form.errors)


class DeviceActivationFormTestCase(TestCase):

    def test_valid_code(self):
        device = DeviceFactory.create(status='registered')
        form_data = {
            'activation_code': device.activation_code,
        }
        form = DeviceActivationForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.device.pk, device.pk)

    def test_required(self):
        form = DeviceActivationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('activation_code', form.errors)

    def test_already_activated(self):
        device = DeviceFactory.create(status='activation')
        form_data = {
            'activation_code': device.activation_code,
        }
        form = DeviceActivationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Invalid activation code.',
                      form.errors['activation_code'])


class AccountFormTestCase(TestCase):

    def test_create_init(self):
        with self.assertRaises(AssertionError):
            AccountForm()

    def test_update_btc(self):
        account = AccountFactory.create()
        form_data = {
            'max_payout': '0.1',
            'forward_address': '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE',
        }
        form = AccountForm(data=form_data, instance=account)
        self.assertTrue(form.is_valid())
        account_updated = form.save()
        self.assertEqual(account_updated.pk, account.pk)
        self.assertEqual(account_updated.currency.pk,
                         account.currency.pk)
        self.assertEqual(account_updated.max_payout, Decimal('0.1'))

    def test_update_btc_no_data(self):
        account = AccountFactory.create()
        form_data = {}
        form = AccountForm(data=form_data, instance=account)
        self.assertFalse(form.is_valid())
        self.assertIn('max_payout', form.errors)
        self.assertIn('forward_address', form.errors)

    def test_update_btc_invalid_forward_address(self):
        account = AccountFactory.create(currency__name='TBTC')
        form_data = {
            'max_payout': '0.1',
            'forward_address': '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE',
        }
        form = AccountForm(data=form_data, instance=account)
        self.assertFalse(form.is_valid())
        self.assertIn('forward_address', form.errors)

    def test_update_gbp(self):
        account = AccountFactory.create(currency__name='GBP')
        btc = CurrencyFactory.create(name='BTC')
        form_data = {'currency': btc.pk}
        form = AccountForm(data=form_data, instance=account)
        self.assertTrue(form.is_valid())
        account_updated = form.save()
        self.assertEqual(account_updated.currency.pk,
                         account.currency.pk)

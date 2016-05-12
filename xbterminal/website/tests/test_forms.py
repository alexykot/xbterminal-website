from django.test import TestCase
from django.core import mail
from mock import patch

from oauth2_provider.models import Application
from website.models import MerchantAccount, INSTANTFIAT_PROVIDERS
from website.forms import (
    MerchantRegistrationForm,
    ResetPasswordForm,
    ProfileForm,
    DeviceForm,
    DeviceActivationForm)
from website.tests.factories import (
    MerchantAccountFactory,
    AccountFactory,
    DeviceFactory)
from operations.exceptions import CryptoPayUserAlreadyExists


class MerchantRegistrationFormTestCase(TestCase):

    @patch('website.forms.cryptopay.create_merchant')
    def test_valid_data(self, cryptopay_mock):
        cryptopay_mock.return_value = ('merchant_id', 'x1y2z3')
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
        self.assertEqual(merchant.company_name, form_data['company_name'])
        self.assertEqual(merchant.user.email, form_data['contact_email'])
        self.assertEqual(merchant.language.code, 'en')
        self.assertEqual(merchant.currency.name, 'GBP')
        # Oauth
        oauth_app = Application.objects.get(user=merchant.user)
        self.assertEqual(oauth_app.client_id, form_data['contact_email'])
        # Accounts
        self.assertEqual(merchant.account_set.count(), 4)
        account_btc = merchant.account_set.get(currency__name='BTC')
        self.assertEqual(account_btc.balance, 0)
        self.assertEqual(account_btc.balance_max, 0)
        self.assertEqual(merchant.get_account_balance('BTC'), 0)
        self.assertIsNone(merchant.get_account_balance('TBTC'))
        account_gbp = merchant.account_set.get(currency__name='GBP')
        self.assertEqual(account_gbp.balance, 0)
        self.assertEqual(account_gbp.balance_max, 0)
        self.assertEqual(account_gbp.instantfiat_provider,
                         INSTANTFIAT_PROVIDERS.CRYPTOPAY)
        self.assertEqual(account_gbp.instantfiat_merchant_id, 'merchant_id')
        self.assertEqual(account_gbp.instantfiat_api_key, 'x1y2z3')
        self.assertTrue(merchant.account_set.filter(
            currency__name='USD').exists())
        self.assertTrue(merchant.account_set.filter(
            currency__name='EUR').exists())
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

    @patch('website.forms.cryptopay.create_merchant')
    @patch('website.forms.send_registration_email')
    def test_send_email_error(self, send_mock, cryptopay_mock):
        send_mock.side_effect = ValueError
        cryptopay_mock.return_value = ('merchant_id', 'a1b2c3')
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
        merchant = MerchantAccountFactory.create(
            gocoin_merchant_id='test')
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
        self.assertEqual(merchant_updated.company_name, form_data['company_name'])


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
            'bitcoin_address': '1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6',
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
            'bitcoin_address': '1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6',
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

    def test_invalid_bitcoin_address(self):
        merchant = MerchantAccountFactory.create()
        account = AccountFactory.create(merchant=merchant)
        form_data = {
            'device_type': 'hardware',
            'name': 'Terminal',
            'account': account.pk,
            'bitcoin_address': 'xxx',
        }
        form = DeviceForm(data=form_data, merchant=merchant)
        self.assertFalse(form.is_valid())
        self.assertIn('bitcoin_address', form.errors)

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

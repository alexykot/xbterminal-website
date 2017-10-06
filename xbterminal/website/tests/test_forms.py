# -*- coding: utf-8 -*-
from decimal import Decimal

from django.test import TestCase
from django.core import mail
from django.utils.datastructures import MultiValueDict

from mock import patch
from oauth2_provider.models import Application

from transactions.tests.factories import BalanceChangeFactory
from website.models import MerchantAccount
from website.forms import (
    LoginMethodForm,
    MerchantRegistrationForm,
    ResetPasswordForm,
    ProfileForm,
    KYCDocumentUploadForm,
    DeviceForm,
    DeviceActivationForm,
    AccountForm,
    TransactionSearchForm,
    WithdrawToBankAccountForm)
from website.tests.factories import (
    create_uploaded_image,
    MerchantAccountFactory,
    AccountFactory,
    DeviceFactory)


class LoginMethodFormTestCase(TestCase):

    def test_valid_data(self):
        form_data = {'method': 'login'}
        form = LoginMethodForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['method'], 'login')

    def test_required(self):
        form = LoginMethodForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['method'][0],
                         'Please choose how to login.')


class MerchantRegistrationFormTestCase(TestCase):

    def test_valid_data(self):
        form_data = {
            'company_name': 'Test Company ',
            'business_address': 'Test Address',
            'town': 'Test Town',
            'country': 'GB',
            'post_code': '123456',
            'contact_first_name': u'Тест',
            'contact_last_name': u'Тест',
            'contact_email': 'test@example.net',
            'contact_phone': '+123456789',
            'terms': 'on',
        }
        form = MerchantRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        merchant = form.save()
        self.assertEqual(merchant.company_name, 'Test Company')
        self.assertEqual(merchant.contact_first_name,
                         form_data['contact_first_name'])
        self.assertEqual(merchant.contact_last_name,
                         form_data['contact_last_name'])
        self.assertEqual(merchant.user.email, form_data['contact_email'])
        self.assertEqual(merchant.language.code, 'en')
        self.assertEqual(merchant.currency.name, 'GBP')
        self.assertIsNone(merchant.instantfiat_provider)
        self.assertIsNone(merchant.instantfiat_merchant_id)
        self.assertIsNone(merchant.instantfiat_email)
        self.assertIsNone(merchant.instantfiat_api_key)
        # Oauth
        oauth_app = Application.objects.get(user=merchant.user)
        self.assertEqual(oauth_app.client_id, form_data['contact_email'])
        # Accounts
        self.assertEqual(merchant.account_set.count(), 1)
        account_btc_internal = merchant.account_set.get(
            currency__name='BTC', instantfiat=False)
        self.assertEqual(account_btc_internal.balance, 0)
        self.assertEqual(account_btc_internal.balance_max, 0)
        self.assertIsNone(account_btc_internal.instantfiat_account_id)
        # Email
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0], form_data['contact_email'])

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
        self.assertEqual(form.errors['terms'][0],
                         'Please accept terms & conditions.')

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
            'terms': 'on',
        }
        form = MerchantRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['contact_first_name'][0],
            'Enter a valid name. This value may contain only letters.')
        self.assertEqual(
            form.errors['contact_last_name'][0],
            'Enter a valid name. This value may contain only letters.')

    @patch('website.forms.send_registration_email')
    def test_send_email_error(self, send_mock):
        send_mock.side_effect = ValueError
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
            'terms': 'on',
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


class KYCDocumentUploadFormTestCase(TestCase):

    def test_upload(self):
        files = MultiValueDict({'file': [create_uploaded_image(100)]})
        form = KYCDocumentUploadForm(data={}, files=files)
        self.assertIsNone(form.document_type)
        self.assertTrue(form.is_valid())
        document = form.save(commit=False)
        self.assertIsNotNone(document.file)

    def test_max_length_error(self):
        image = create_uploaded_image(100, name='a' * 100 + '.png')
        files = MultiValueDict({'file': [image]})
        form = KYCDocumentUploadForm(data={}, files=files)
        self.assertIs(form.is_valid(), False)
        self.assertIn('file', form.errors)


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

    def test_update_valid_hardware(self):
        device = DeviceFactory.create(device_type='hardware')
        form_data = {
            'device_type': 'hardware',
            'name': 'New Name',
            'account': device.account.pk,
            'amount_1': '0.1',
            'amount_2': '0.2',
            'amount_3': '0.3',
            'amount_shift': '0.01',
            'max_payout': '10.0',
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
        self.assertEqual(device.amount_1, Decimal('0.10'))
        self.assertEqual(device.amount_2, Decimal('0.20'))
        self.assertEqual(device.amount_3, Decimal('0.30'))
        self.assertEqual(device.amount_shift, Decimal('0.01'))
        self.assertEqual(device.max_payout, Decimal('10.0'))

    def test_update_valid_mobile(self):
        device = DeviceFactory.create(device_type='mobile')
        form_data = {
            'device_type': 'mobile',
            'name': 'New Name',
            'account': device.account.pk,
        }
        form = DeviceForm(data=form_data,
                          merchant=device.merchant,
                          instance=device)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.device_type_verbose(), 'Mobile app')
        device = form.save()
        self.assertEqual(device.device_type, 'mobile')
        self.assertEqual(device.name, form_data['name'])
        self.assertEqual(device.status, 'active')

    def test_required_hardware(self):
        merchant = MerchantAccountFactory.create()
        device = DeviceFactory.create(device_type='hardware')
        form = DeviceForm(data={}, merchant=merchant, instance=device)
        self.assertFalse(form.is_valid())
        self.assertIn('device_type', form.errors)
        self.assertIn('name', form.errors)
        self.assertIn('account', form.errors)
        self.assertIn('amount_1', form.errors)
        self.assertIn('amount_2', form.errors)
        self.assertIn('amount_3', form.errors)
        self.assertIn('amount_shift', form.errors)
        self.assertIn('max_payout', form.errors)

    def test_required_mobile(self):
        merchant = MerchantAccountFactory.create()
        device = DeviceFactory.create(device_type='mobile')
        form = DeviceForm(data={}, merchant=merchant, instance=device)
        self.assertFalse(form.is_valid())
        self.assertIn('device_type', form.errors)
        self.assertIn('name', form.errors)
        self.assertIn('account', form.errors)
        self.assertNotIn('amount_1', form.errors)
        self.assertNotIn('amount_2', form.errors)
        self.assertNotIn('amount_3', form.errors)
        self.assertNotIn('amount_shift', form.errors)
        self.assertNotIn('max_payout', form.errors)

    def test_invalid_account_currency(self):
        merchant = MerchantAccountFactory.create()
        account = AccountFactory.create(merchant=merchant,
                                        currency__name='USD')
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
        device = DeviceFactory.create(status='activation_in_progress')
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

        account = AccountFactory.create(currency__name='USD',
                                        instantfiat=False)
        with self.assertRaises(AssertionError):
            AccountForm(instance=account)

    def test_update_btc(self):
        account = AccountFactory.create()
        form_data = {
            'forward_address': '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE',
        }
        form = AccountForm(data=form_data, instance=account)
        self.assertTrue(form.is_valid())
        account_updated = form.save()
        self.assertEqual(account_updated.pk, account.pk)
        self.assertEqual(account_updated.currency.pk,
                         account.currency.pk)

    def test_update_btc_no_data(self):
        account = AccountFactory.create()
        form_data = {}
        form = AccountForm(data=form_data, instance=account)
        self.assertFalse(form.is_valid())
        self.assertIn('forward_address', form.errors)

    def test_update_btc_invalid_forward_address(self):
        account = AccountFactory.create(currency__name='TBTC')
        form_data = {
            'forward_address': '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE',
        }
        form = AccountForm(data=form_data, instance=account)
        self.assertFalse(form.is_valid())
        self.assertIn('forward_address', form.errors)

    def test_update_gbp(self):
        account = AccountFactory.create(currency__name='GBP')
        form_data = {
            'bank_account_name': 'Test',
            'bank_account_bic': 'DEUTDEFF000',
            'bank_account_iban': 'GB82WEST12345698765432',
        }
        form = AccountForm(data=form_data, instance=account)
        self.assertTrue(form.is_valid())
        account_updated = form.save()
        self.assertEqual(account_updated.bank_account_name,
                         form_data['bank_account_name'])
        self.assertEqual(account_updated.bank_account_bic,
                         form_data['bank_account_bic'])
        self.assertEqual(account_updated.bank_account_iban,
                         form_data['bank_account_iban'])

    def test_update_gbp_no_data(self):
        account = AccountFactory.create(currency__name='GBP')
        form_data = {}
        form = AccountForm(data=form_data, instance=account)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['bank_account_name'][0],
                         'This field is required.')
        self.assertEqual(form.errors['bank_account_bic'][0],
                         'This field is required.')
        self.assertEqual(form.errors['bank_account_iban'][0],
                         'This field is required.')

    def test_update_gbp_invalid_bic(self):
        account = AccountFactory.create(currency__name='GBP')
        form_data = {
            'bank_account_name': 'Test',
            'bank_account_bic': 'XXX000AAA',
            'bank_account_iban': 'GB82WEST12345698765432',
        }
        form = AccountForm(data=form_data, instance=account)
        self.assertFalse(form.is_valid())
        self.assertIn('bank_account_bic', form.errors)

    def test_update_gbp_invalid_iban(self):
        account = AccountFactory.create(currency__name='GBP')
        form_data = {
            'bank_account_name': 'Test',
            'bank_account_bic': 'DEUTDEFF000',
            'bank_account_iban': 'GB82WEST12345698765433',
        }
        form = AccountForm(data=form_data, instance=account)
        self.assertFalse(form.is_valid())
        self.assertIn('bank_account_iban', form.errors)


class TransactionSearchFormTestCase(TestCase):

    def test_valid_data(self):
        data = {
            'range_beg': '2016-10-25',
            'range_end': '2016-10-27',
        }
        form = TransactionSearchForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['range_beg'].day, 25)
        self.assertEqual(form.cleaned_data['range_end'].day, 27)

    def test_required(self):
        form = TransactionSearchForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['range_beg'][0],
                         'This field is required.')
        self.assertEqual(form.errors['range_end'][0],
                         'This field is required.')

    def test_compare(self):
        data = {
            'range_beg': '2016-10-20',
            'range_end': '2016-09-29',
        }
        form = TransactionSearchForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['range_end'][0],
                         'Second date must not be earlier than the first.')


class WithdrawToBankAccountFormTestCase(TestCase):

    def test_valid_data(self):
        account = AccountFactory.create(instantfiat=True)
        device = DeviceFactory.create(merchant=account.merchant,
                                      account=account,
                                      max_payout=Decimal('0.2'))
        # WARNING: fiat deposits are not implemented
        BalanceChangeFactory(
            deposit__account=account,
            deposit__device=device,
            deposit__confirmed=True,
            amount=Decimal('1.0'))
        DeviceFactory.create(merchant=account.merchant, account=account)
        self.assertEqual(account.balance_confirmed, Decimal('1.0'))
        self.assertEqual(account.balance_min, Decimal('0.2'))
        data = {'amount': '0.5'}
        form = WithdrawToBankAccountForm(data=data, account=account)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['amount'], Decimal('0.5'))

    def test_required(self):
        account = AccountFactory.create(instantfiat=True)
        form = WithdrawToBankAccountForm(data={}, account=account)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['amount'][0],
                         'This field is required.')

    def test_insufficient_balance(self):
        account = AccountFactory.create(instantfiat=True)
        BalanceChangeFactory(
            deposit__account=account,
            deposit__confirmed=True,
            deposit__merchant_coin_amount=Decimal('0.1'))
        data = {'amount': '0.2'}
        form = WithdrawToBankAccountForm(data=data, account=account)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['amount'][0],
                         'Insufficient balance on account.')

    def test_min_balance(self):
        account = AccountFactory.create(instantfiat=True)
        BalanceChangeFactory(
            deposit__account=account,
            deposit__confirmed=True,
            deposit__merchant_coin_amount=Decimal('0.5'))
        DeviceFactory.create(merchant=account.merchant,
                             account=account,
                             max_payout=Decimal('0.2'))
        self.assertEqual(account.balance_min, Decimal('0.2'))
        data = {'amount': '0.4'}
        form = WithdrawToBankAccountForm(data=data, account=account)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['amount'][0],
                         'Account balance can not go below the minimum value.')

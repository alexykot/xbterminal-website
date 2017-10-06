import mock
from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from website.tests.factories import (
    CurrencyFactory,
    MerchantAccountFactory,
    AccountFactory,
    DeviceFactory)
from website.models import Account, Device
from website.admin import AccountAdmin, DeviceAdmin


class AccountAdminTestCase(TestCase):

    def setUp(self):
        self.ma = AccountAdmin(Account, AdminSite())

    def test_create_instantfiat(self):
        merchant = MerchantAccountFactory.create()
        form_cls = self.ma.get_form(mock.Mock(), None)
        data = {
            'merchant': merchant.pk,
            'currency': merchant.currency.pk,
            'max_payout': '0.00',
            'forward_address': '',
            'instantfiat': True,
            'instantfiat_account_id': 'test',
        }
        form = form_cls(data=data)
        self.assertTrue(form.is_valid())
        account = form.save()
        self.assertEqual(account.instantfiat_account_id,
                         data['instantfiat_account_id'])

    def test_create_instantfiat_error(self):
        merchant = MerchantAccountFactory.create()
        form_cls = self.ma.get_form(mock.Mock(), None)
        data = {
            'merchant': merchant.pk,
            'currency': merchant.currency.pk,
            'max_payout': '0.00',
            'forward_address': '',
            'instantfiat': True,
        }
        form = form_cls(data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['instantfiat_account_id'][0],
                         'This field is required.')

    def test_create_btc_error(self):
        merchant = MerchantAccountFactory.create()
        form_cls = self.ma.get_form(mock.Mock(), None)
        btc = CurrencyFactory.create(name='BTC')
        data = {
            'merchant': merchant.pk,
            'currency': btc.pk,
            'max_payout': '0.00',
            'forward_address': '',
            'instantfiat': False,
        }
        form = form_cls(data=data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['forward_address'][0],
                         'This field is required.')

    def test_update_btc(self):
        account = AccountFactory.create()
        data = {
            'merchant': account.merchant.pk,
            'currency': account.currency.pk,
            'max_payout': '1.00',
            'forward_address': '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE',
            'instantfiat': False,
        }
        form_cls = self.ma.get_form(mock.Mock(), account)
        form = form_cls(data=data, instance=account)
        self.assertTrue(form.is_valid())
        account_updated = form.save()
        self.assertEqual(account_updated.pk, account.pk)


class DeviceAdminTestCase(TestCase):

    def setUp(self):
        self.ma = DeviceAdmin(Device, AdminSite())

    def test_update(self):
        device = DeviceFactory(
            our_fee_override='1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE')
        data = {
            'merchant': device.merchant.pk,
            'account': device.account.pk,
            'device_type': device.device_type,
            'name': device.name,
            'batch': device.batch.pk,
            'api_key': device.api_key,
            'our_fee_override': device.our_fee_override,
            'amount_1': device.amount_1,
            'amount_2': device.amount_2,
            'amount_3': device.amount_3,
            'amount_shift': device.amount_shift,
            'max_payout': device.max_payout,
        }
        form_cls = self.ma.get_form(mock.Mock(), device)
        form = form_cls(data=data, instance=device)
        self.assertIs(form.is_valid(), True)
        device_updated = form.save()
        self.assertEqual(device_updated.pk, device.pk)

from django.test import TestCase

from website.models import User
from website.tests.factories import (
    UserFactory,
    MerchantAccountFactory,
    DeviceFactory,
    PaymentOrderFactory)


class UserTestCase(TestCase):

    def test_create_user(self):
        user = User.objects.create(email='test@example.com')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_user_factory(self):
        user = UserFactory.create()
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password('password'))

    def test_get_full_name(self):
        user = UserFactory.create()
        self.assertEqual(user.get_full_name(), user.email)


class MerchantAccountTestCase(TestCase):

    fixtures = ['initial_data.json']

    def test_merchant_factory(self):
        merchant = MerchantAccountFactory.create()
        self.assertEqual(merchant.language.code, 'en')
        self.assertEqual(merchant.currency.name, 'GBP')
        self.assertEqual(merchant.payment_processor, 'gocoin')
        self.assertEqual(merchant.verification_status, 'unverified')


class DeviceTestCase(TestCase):

    fixtures = ['initial_data.json']

    def test_device_factory(self):
        device = DeviceFactory.create()
        self.assertEqual(device.status, 'active')
        self.assertEqual(len(device.key), 8)
        self.assertEqual(device.bitcoin_network, 'mainnet')


class PaymentOrderTestCase(TestCase):

    fixtures = ['initial_data.json']

    def test_payment_order_factory(self):
        payment_order = PaymentOrderFactory.create()
        self.assertEqual(len(payment_order.uid), 6)
        self.assertEqual(payment_order.status, 'new')

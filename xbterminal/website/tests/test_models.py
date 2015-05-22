import datetime
from django.test import TestCase
from django.utils import timezone

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

    def test_status(self):
        # Without instantfiat
        payment_order = PaymentOrderFactory.create()
        self.assertEqual(payment_order.status, 'new')
        payment_order.time_recieved = (payment_order.time_created +
                                       datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'recieved')
        self.assertFalse(payment_order.is_receipt_ready())
        payment_order.time_forwarded = (payment_order.time_recieved +
                                        datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'processed')
        self.assertTrue(payment_order.is_receipt_ready())
        payment_order.time_finished = (payment_order.time_forwarded +
                                       datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'completed')
        # With instantfiat
        payment_order = PaymentOrderFactory.create(
            instantfiat_invoice_id='invoice01')
        self.assertEqual(payment_order.status, 'new')
        payment_order.time_recieved = (payment_order.time_created +
                                       datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'recieved')
        self.assertFalse(payment_order.is_receipt_ready())
        payment_order.time_forwarded = (payment_order.time_recieved +
                                        datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'forwarded')
        self.assertTrue(payment_order.is_receipt_ready())
        payment_order.time_exchanged = (payment_order.time_forwarded +
                                        datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'processed')
        payment_order.time_finished = (payment_order.time_exchanged +
                                       datetime.timedelta(minutes=1))
        self.assertEqual(payment_order.status, 'completed')
        # Timeout
        payment_order = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(payment_order.status, 'timeout')
        # Failed
        payment_order = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=2),
            time_recieved=timezone.now() - datetime.timedelta(hours=1))
        self.assertEqual(payment_order.status, 'failed')

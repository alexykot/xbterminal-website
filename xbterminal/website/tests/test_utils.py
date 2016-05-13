from django.conf import settings
from django.core import mail
from django.test import TestCase

from website.utils.accounts import check_managed_accounts
from website.utils.email import send_error_message
from website.tests.factories import (
    MerchantAccountFactory,
    AccountFactory)
from operations.tests.factories import (
    PaymentOrderFactory,
    WithdrawalOrderFactory)


class AccountsUtilsTestCase(TestCase):

    def test_check_managed_accounts(self):
        merchant = MerchantAccountFactory.create()
        self.assertFalse(check_managed_accounts(merchant))
        AccountFactory.create(
            merchant=merchant,
            currency__name='GBP',
            instantfiat_merchant_id='test')
        self.assertFalse(check_managed_accounts(merchant))
        AccountFactory.create(
            merchant=merchant,
            currency__name='USD',
            instantfiat_merchant_id='test')
        self.assertFalse(check_managed_accounts(merchant))
        AccountFactory.create(
            merchant=merchant,
            currency__name='EUR',
            instantfiat_merchant_id='test')
        self.assertTrue(check_managed_accounts(merchant))


class EmailUtilsTestCase(TestCase):

    def test_error_message_payment(self):
        order = PaymentOrderFactory.create()
        send_error_message(order=order)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to,
                         settings.CONTACT_EMAIL_RECIPIENTS)

    def test_error_message_withdrawal(self):
        order = WithdrawalOrderFactory.create()
        send_error_message(order=order)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to,
                         settings.CONTACT_EMAIL_RECIPIENTS)

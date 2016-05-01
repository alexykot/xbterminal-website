from django.conf import settings
from django.core import mail
from django.test import TestCase

from website.utils.email import send_error_message
from operations.tests.factories import (
    PaymentOrderFactory,
    WithdrawalOrderFactory)


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

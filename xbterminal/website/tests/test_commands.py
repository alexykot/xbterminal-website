from decimal import Decimal
from django.test import TestCase
from django.core import mail
from django.conf import settings
from mock import patch, Mock

from website.tests.factories import BTCAccountFactory
from website.management.commands.check_wallet import check_wallet


class CheckWalletTestCase(TestCase):

    fixtures = ['initial_data.json']

    @patch('website.management.commands.check_wallet.BlockChain')
    @patch('website.utils.send_balance_admin_notification')
    def test_command_ok(self, send_ntf_mock, bc_mock):
        BTCAccountFactory.create_batch(
            2, network='mainnet', balance=Decimal('0.2'))
        bc_mock.return_value = Mock(**{
            'get_balance.return_value': Decimal('0.4'),
        })
        check_wallet('mainnet')
        self.assertFalse(send_ntf_mock.called)

    @patch('website.management.commands.check_wallet.BlockChain')
    def test_mismatch(self, bc_mock):
        BTCAccountFactory.create_batch(
            2, network='mainnet', balance=Decimal('0.2'))
        bc_mock.return_value = Mock(**{
            'get_balance.return_value': Decimal('0.5'),
        })
        check_wallet('mainnet')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(settings.CONTACT_EMAIL_RECIPIENTS[0],
                      mail.outbox[0].to)
        self.assertIn('mainnet', mail.outbox[0].body)

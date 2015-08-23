from decimal import Decimal
from django.test import TestCase
from django.core import mail
from django.conf import settings
from mock import patch, Mock

from website.tests.factories import BTCAccountFactory
from website.management.commands.check_wallet import \
    check_wallet, check_wallet_strict


class CheckWalletTestCase(TestCase):

    @patch('website.management.commands.check_wallet.BlockChain')
    @patch('website.utils.send_balance_admin_notification')
    def test_check_ok(self, send_ntf_mock, bc_mock):
        BTCAccountFactory.create_batch(
            2, network='mainnet', balance=Decimal('0.2'))
        bc_mock.return_value = Mock(**{
            'get_balance.return_value': Decimal('0.4'),
            'get_address_balance.return_value': Decimal('0.2'),
        })
        check_wallet('mainnet')
        check_wallet_strict('mainnet')
        self.assertFalse(send_ntf_mock.called)

    @patch('website.management.commands.check_wallet.BlockChain')
    def test_check_mismatch(self, bc_mock):
        BTCAccountFactory.create_batch(
            2, network='mainnet', balance=Decimal('0.2'))
        bc_mock.return_value = Mock(**{
            'get_address_balance.return_value': Decimal('0.3'),
        })
        check_wallet('mainnet')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(settings.CONTACT_EMAIL_RECIPIENTS[0],
                      mail.outbox[0].to)
        self.assertIn('mainnet', mail.outbox[0].body)

    @patch('website.management.commands.check_wallet.BlockChain')
    def test_strict_check_mismatch(self, bc_mock):
        BTCAccountFactory.create_batch(
            2, network='mainnet', balance=Decimal('0.2'))
        bc_mock.return_value = Mock(**{
            'get_balance.return_value': Decimal('0.5'),
        })
        check_wallet_strict('mainnet')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(settings.CONTACT_EMAIL_RECIPIENTS[0],
                      mail.outbox[0].to)
        self.assertIn('mainnet', mail.outbox[0].body)

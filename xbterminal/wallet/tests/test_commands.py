import StringIO
from mock import patch

from django.test import TestCase
from django.core.management import call_command

from wallet.constants import BIP44_PURPOSE, BIP44_COIN_TYPES
from wallet.models import WalletKey
from wallet.utils.keys import create_master_key, create_wallet_key


class CreateKeysTestCase(TestCase):

    def setUp(self):
        master_key = create_master_key('test')
        self.btc_private_key = create_wallet_key(
            master_key, BIP44_PURPOSE, 'BTC', BIP44_COIN_TYPES.BTC)

    @patch('wallet.management.commands.create_keys.get_input')
    def test_from_secret(self, input_mock):
        input_mock.return_value = 'test'
        buffer = StringIO.StringIO()
        call_command('create_keys', from_secret=True, stdout=buffer)

        self.assertEqual(input_mock.call_count, 1)
        self.assertEqual(input_mock.call_args[0][0], 'Secret: ')
        self.assertEqual(WalletKey.objects.count(), 4)

        btc_key = WalletKey.objects.get(coin_type=BIP44_COIN_TYPES.BTC)
        self.assertEqual(btc_key.private_key, self.btc_private_key)
        self.assertEqual(btc_key.walletaccount_set.count(), 1)
        self.assertIn('Wallet key for coin BTC saved to database.',
                      buffer.getvalue())
        tbtc_key = WalletKey.objects.get(coin_type=BIP44_COIN_TYPES.TBTC)
        self.assertIs(tbtc_key.private_key.startswith('tprv'), True)
        self.assertEqual(tbtc_key.walletaccount_set.count(), 1)
        self.assertIn('Wallet key for coin TBTC saved to database.',
                      buffer.getvalue())

    @patch('wallet.management.commands.create_keys.get_input')
    def test_already_exists(self, input_mock):
        input_mock.return_value = 'test'
        WalletKey.objects.create(
            coin_type=BIP44_COIN_TYPES.BTC,
            private_key=self.btc_private_key)
        buffer = StringIO.StringIO()
        call_command('create_keys', from_secret=True, stdout=buffer)

        self.assertEqual(WalletKey.objects.count(), 4)
        self.assertIn('Wallet key for coin BTC already exists.',
                      buffer.getvalue())

    @patch('wallet.management.commands.create_keys.get_input')
    def test_invalid_master_key(self, input_mock):
        input_mock.return_value = 'test'
        buffer = StringIO.StringIO()
        call_command('create_keys', stdout=buffer)

        self.assertEqual(input_mock.call_count, 1)
        self.assertEqual(input_mock.call_args[0][0], 'Master key: ')
        self.assertIn('Invalid master key.', buffer.getvalue())
        self.assertEqual(WalletKey.objects.count(), 0)

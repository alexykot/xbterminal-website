import StringIO

from django.test import TestCase
from django.core.management import call_command

from wallet.enums import BIP44_COIN_TYPES
from wallet.models import WalletKey


class CreateKeysTestCase(TestCase):

    def test_create_keys(self):
        buffer = StringIO.StringIO()
        call_command('create_keys', stdout=buffer)
        btc_key = WalletKey.objects.get(coin_type=BIP44_COIN_TYPES.BTC)
        self.assertEqual(btc_key.walletaccount_set.count(), 1)
        xtn_key = WalletKey.objects.get(coin_type=BIP44_COIN_TYPES.XTN)
        self.assertEqual(xtn_key.walletaccount_set.count(), 1)
        self.assertEqual(len(buffer.getvalue().splitlines()), 3)

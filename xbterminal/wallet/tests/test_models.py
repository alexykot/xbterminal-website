from django.db import IntegrityError
from django.test import TestCase

from wallet.models import WalletKey
from wallet.enums import BIP44_COIN_TYPES
from wallet.tests.factories import WalletKeyFactory


class WalletKeyTestCase(TestCase):

    def test_create(self):
        key = WalletKey.objects.create(
            coin_type=BIP44_COIN_TYPES.BTC,
            private_key='a' * 100)
        self.assertIsNotNone(key.added_at)
        self.assertEqual(key.path, "0'/0'")
        self.assertEqual(str(key), key.path)

    def test_factory(self):
        key = WalletKeyFactory()
        self.assertEqual(key.coin_type, BIP44_COIN_TYPES.BTC)
        self.assertGreater(len(key.private_key), 100)
        self.assertEqual(key.path, "0'/0'")

    def test_unique_coin_type(self):
        WalletKeyFactory(coin_type=BIP44_COIN_TYPES.BTC)
        with self.assertRaises(IntegrityError):
            WalletKeyFactory(coin_type=BIP44_COIN_TYPES.BTC)

    def test_unique_private_key(self):
        WalletKeyFactory(private_key='a' * 100)
        with self.assertRaises(IntegrityError):
            WalletKeyFactory(private_key='a' * 100)

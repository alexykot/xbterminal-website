from django.db import IntegrityError
from django.test import TestCase

from wallet.models import WalletKey, WalletAccount, Address
from wallet.enums import BIP44_COIN_TYPES
from wallet.tests.factories import (
    WalletKeyFactory,
    WalletAccountFactory,
    AddressFactory)


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


class WalletAccountTestCase(TestCase):

    def test_create(self):
        key = WalletKeyFactory()
        account = WalletAccount.objects.create(
            parent_key=key)
        self.assertEqual(account.index, 0)
        self.assertEqual(account.path, "0'/0'/0")
        self.assertEqual(str(account), account.path)

    def test_factory(self):
        account = WalletAccountFactory()
        self.assertEqual(account.path, "0'/0'/0")


class AddressTestCase(TestCase):

    def test_create(self):
        account = WalletAccountFactory()
        address = Address.objects.create(
            wallet_account=account,
            is_change=False)
        self.assertIs(address.is_change, False)
        self.assertEqual(address.index, 0)
        self.assertIs(address.address.startswith('1'), True)
        self.assertEqual(address.relative_path, '0/0/0')
        self.assertEqual(str(address), address.address)

    def test_factory(self):
        address = AddressFactory()
        self.assertIs(address.address.startswith('1'), True)
        self.assertEqual(address.relative_path, '0/0/0')

    def test_unique_index(self):
        account = WalletAccountFactory()
        address_1 = AddressFactory(wallet_account=account)
        address_2 = AddressFactory(wallet_account=account)
        with self.assertRaises(IntegrityError):
            address_2.index = address_1.index
            address_2.save()

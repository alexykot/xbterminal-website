from django.db import IntegrityError
from django.test import TestCase

from wallet.models import WalletKey, WalletAccount, Address
from wallet.constants import BIP44_COIN_TYPES, MAX_INDEX
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

    def test_factory_btc(self):
        key = WalletKeyFactory()
        self.assertEqual(key.coin_type, BIP44_COIN_TYPES.BTC)
        self.assertGreater(len(key.private_key), 100)
        self.assertEqual(key.path, "0'/0'")
        self.assertIs(key.private_key.startswith('xprv'), True)

    def test_factory_tbtc(self):
        key = WalletKeyFactory(coin_type=BIP44_COIN_TYPES.TBTC)
        self.assertEqual(key.path, "0'/1'")
        self.assertIs(key.private_key.startswith('tprv'), True)

    def test_factory_already_created(self):
        key_1 = WalletKeyFactory()
        key_2 = WalletKeyFactory()
        self.assertEqual(key_2.pk, key_1.pk)

    def test_unique_coin_type(self):
        WalletKey.objects.create(coin_type=BIP44_COIN_TYPES.BTC,
                                 private_key='a' * 100)
        with self.assertRaises(IntegrityError):
            WalletKey.objects.create(coin_type=BIP44_COIN_TYPES.BTC,
                                     private_key='b' * 100)

    def test_unique_private_key(self):
        WalletKey.objects.create(coin_type=BIP44_COIN_TYPES.BTC,
                                 private_key='a' * 100)
        with self.assertRaises(IntegrityError):
            WalletKey.objects.create(coin_type=BIP44_COIN_TYPES.TBTC,
                                     private_key='a' * 100)


class WalletAccountTestCase(TestCase):

    def test_create(self):
        key = WalletKeyFactory()
        account = WalletAccount.objects.create(parent_key=key)
        self.assertEqual(account.index, 0)
        self.assertEqual(account.path, "0'/0'/0")
        self.assertEqual(str(account), account.path)
        account_next = WalletAccount.objects.create(parent_key=key)
        self.assertEqual(account_next.index, 1)

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
        address_next = account.address_set.create(is_change=False)
        self.assertEqual(address_next.index, 1)
        address_change = account.address_set.create(is_change=True)
        self.assertEqual(address_change.index, 0)

    def test_factory_btc(self):
        address = AddressFactory()
        self.assertIs(address.address.startswith('1'), True)
        self.assertEqual(address.relative_path, '0/0/0')

    def test_factory_tbtc(self):
        address = AddressFactory(
            wallet_account__parent_key__coin_type=BIP44_COIN_TYPES.TBTC)
        self.assertIn(address.address[0], ['m', 'n'])

    def test_unique_index(self):
        account = WalletAccountFactory()
        address_1 = AddressFactory(wallet_account=account)
        address_2 = AddressFactory(wallet_account=account)
        with self.assertRaises(IntegrityError):
            address_2.index = address_1.index
            address_2.save()

    def test_create_method(self):
        wallet_key = WalletKeyFactory(coin_type=BIP44_COIN_TYPES.BTC)
        self.assertEqual(wallet_key.walletaccount_set.count(), 0)
        address_1 = Address.create('BTC')
        self.assertEqual(wallet_key.walletaccount_set.count(), 1)
        self.assertEqual(address_1.wallet_account.parent_key, wallet_key)
        self.assertIs(address_1.is_change, False)
        self.assertEqual(address_1.index, 0)
        address_2 = Address.create('BTC', is_change=True)
        self.assertEqual(wallet_key.walletaccount_set.count(), 2)
        self.assertIs(address_2.is_change, True)
        self.assertEqual(address_2.index, 0)

    def test_create_method_tbtc(self):
        wallet_key = WalletKeyFactory(coin_type=BIP44_COIN_TYPES.TBTC)
        address = Address.create('TBTC')
        self.assertEqual(address.wallet_account.parent_key, wallet_key)

    def test_create_method_max_index(self):
        wallet_key = WalletKeyFactory(coin_type=BIP44_COIN_TYPES.BTC)
        account = WalletAccountFactory(parent_key=wallet_key)
        self.assertEqual(wallet_key.walletaccount_set.count(), 1)
        address_1 = AddressFactory(wallet_account=account)
        address_1.index = MAX_INDEX + 1
        address_1.save()
        address_2 = Address.create('BTC')
        self.assertNotEqual(address_2.wallet_account,
                            address_1.wallet_account)
        self.assertEqual(wallet_key.walletaccount_set.count(), 2)

    def test_get_private_key(self):
        address = AddressFactory()
        private_key = address.get_private_key()
        self.assertEqual(private_key.address(), address.address)

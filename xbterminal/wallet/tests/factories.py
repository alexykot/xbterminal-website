import factory

from wallet import models
from wallet.enums import BIP44_COIN_TYPES
from wallet.utils.keys import create_master_key, create_wallet_key


class WalletKeyFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.WalletKey

    coin_type = BIP44_COIN_TYPES.BTC

    @factory.lazy_attribute_sequence
    def private_key(self, n):
        netcode = BIP44_COIN_TYPES.for_value(self.coin_type).constant
        master_key = create_master_key(str(n))
        path = "0'/{}'".format(self.coin_type)
        return create_wallet_key(master_key, netcode, path, as_private=True)


class WalletAccountFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.WalletAccount

    parent_key = factory.SubFactory(WalletKeyFactory)


class AddressFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.Address

    wallet_account = factory.SubFactory(WalletAccountFactory)
    is_change = False

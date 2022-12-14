import factory

from wallet import models
from wallet.constants import COINS, BIP44_PURPOSE, BIP44_COIN_TYPES
from wallet.utils.keys import create_master_key, create_wallet_key


class WalletKeyFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.WalletKey
        django_get_or_create = ('coin_type',)

    coin_type = BIP44_COIN_TYPES.BTC

    @factory.lazy_attribute_sequence
    def private_key(self, n):
        master_key = create_master_key(n)
        pycoin_code = COINS.for_coin_type(self.coin_type).pycoin_code
        return create_wallet_key(
            master_key,
            BIP44_PURPOSE,
            pycoin_code,
            self.coin_type)


class WalletAccountFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.WalletAccount

    parent_key = factory.SubFactory(WalletKeyFactory)


class AddressFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.Address

    wallet_account = factory.SubFactory(WalletAccountFactory)
    is_change = False

from django.utils.translation import ugettext_lazy as _

from enum import Enum
from extended_choices import Choices


class COINS(Enum):
    BTC = ('BTC', 0, 'bitcoin', _('Bitcoin'))
    TBTC = ('XTN', 1, 'bitcoin', _('Bitcoin Testnet'))
    DASH = ('DASH', 5, 'dash', _('Dash'))
    TDASH = ('tDASH', 1005, 'dash', _('Dash Testnet'))

    def __init__(self, pycoin_code, bip44_type, uri_prefix, display_name):
        self.pycoin_code = pycoin_code
        self.bip44_type = bip44_type
        self.uri_prefix = uri_prefix
        self.display_name = display_name

    @classmethod
    def for_coin_type(cls, coin_type):
        for coin in cls:
            if coin.bip44_type == coin_type:
                return coin


BIP44_PURPOSE = 0

BIP44_COIN_TYPES = Choices(*(
    (currency_name, coin.bip44_type, coin.display_name)
    for currency_name, coin in COINS.__members__.items()
))

MAX_INDEX = 2 ** 30

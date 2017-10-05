from django.utils.translation import ugettext_lazy as _

from enum import Enum
from extended_choices import Choices


class COINS(Enum):
    BTC = ('BTC', 0, _('Bitcoin'))
    TBTC = ('XTN', 1, _('Bitcoin Testnet'))

    def __init__(self, pycoin_code, bip44_type, display_name):
        self.pycoin_code = pycoin_code
        self.bip44_type = bip44_type
        self.display_name = display_name


BIP44_PURPOSE = 0

BIP44_COIN_TYPES = Choices(*(item.value for item in COINS))

MAX_INDEX = 2 ** 30

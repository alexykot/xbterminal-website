from django.utils.translation import ugettext_lazy as _

from extended_choices import Choices


BIP44_COIN_TYPES = Choices(
    ('BITCOIN', 0, _('Bitcoin')),
    ('BITCOIN_TESTNET', 1, _('Bitcoin Testnet')),
)

from django.utils.translation import ugettext_lazy as _

from extended_choices import Choices

BIP44_PURPOSE = 0

BIP44_COIN_TYPES = Choices(
    ('BTC', 0, _('Bitcoin')),
    ('XTN', 1, _('Bitcoin Testnet')),
)

from decimal import Decimal

from django.utils.translation import ugettext_lazy as _

from extended_choices import Choices

BTC_DEC_PLACES = Decimal('0.00000000')
BTC_MIN_OUTPUT = Decimal('0.00005460')
BTC_MIN_FEE = Decimal('0.00005000')

PAYMENT_TYPES = Choices(
    ('BIP21', 1, _('BIP 0021 (Bitcoin URI)')),
    ('BIP70', 2, _('BIP 0070 (Payment Protocol)')),
)

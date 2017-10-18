import datetime
from decimal import Decimal

from django.utils.translation import ugettext_lazy as _

from extended_choices import Choices

COIN_DEC_PLACES = Decimal('0.00000000')
COIN_MIN_OUTPUT = Decimal('0.00005460')
COIN_MIN_FEE = Decimal('0.00005000')

DEPOSIT_TIMEOUT = datetime.timedelta(minutes=15)
DEPOSIT_CONFIDENCE_TIMEOUT = datetime.timedelta(minutes=30)
DEPOSIT_CONFIRMATION_TIMEOUT = datetime.timedelta(minutes=180)

WITHDRAWAL_TIMEOUT = datetime.timedelta(minutes=5)
WITHDRAWAL_CONFIDENCE_TIMEOUT = datetime.timedelta(minutes=45)
WITHDRAWAL_CONFIRMATION_TIMEOUT = datetime.timedelta(minutes=180)

PAYMENT_TYPES = Choices(
    ('BIP21', 1, _('BIP 0021 (Payment URI)')),
    ('BIP70', 2, _('BIP 0070 (Payment Protocol)')),
)

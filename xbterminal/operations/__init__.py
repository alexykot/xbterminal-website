"""
Operations
"""
import datetime
from decimal import Decimal

FIAT_DEC_PLACES = Decimal('0.00000000')
FIAT_MIN_OUTPUT = Decimal('0.01000000')
BTC_DEC_PLACES = Decimal('0.00000000')
BTC_DEFAULT_FEE = Decimal('0.00010000')
BTC_MIN_OUTPUT = Decimal('0.00005460')

PAYMENT_TIMEOUT = datetime.timedelta(minutes=15)
PAYMENT_VALIDATION_TIMEOUT = datetime.timedelta(minutes=30)
PAYMENT_EXCHANGE_TIMEOUT = datetime.timedelta(minutes=45)
PAYMENT_CONFIRMATION_TIMEOUT = datetime.timedelta(minutes=90)

WITHDRAWAL_TIMEOUT = datetime.timedelta(minutes=10)
WITHDRAWAL_BROADCAST_TIMEOUT = datetime.timedelta(minutes=45)

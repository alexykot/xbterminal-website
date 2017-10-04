"""
Operations
"""
import datetime

PAYMENT_TIMEOUT = datetime.timedelta(minutes=15)
PAYMENT_VALIDATION_TIMEOUT = datetime.timedelta(minutes=30)
PAYMENT_EXCHANGE_TIMEOUT = datetime.timedelta(minutes=45)
PAYMENT_CONFIRMATION_TIMEOUT = datetime.timedelta(minutes=180)

WITHDRAWAL_TIMEOUT = datetime.timedelta(minutes=5)
WITHDRAWAL_BROADCAST_TIMEOUT = datetime.timedelta(minutes=45)
WITHDRAWAL_CONFIRMATION_TIMEOUT = datetime.timedelta(minutes=180)

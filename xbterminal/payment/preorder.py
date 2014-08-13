from decimal import Decimal

from constance import config

from payment.instantfiat import gocoin


def get_terminal_price():
    return config.TERMINAL_PRICE


def get_exchange_rate():
    """
    Get exchange rate from GoCoin
    Returns:
        exchange rate: Decimal
    """
    result = gocoin.create_invoice(
        config.TERMINAL_PRICE,
        'GBP',
        config.GOCOIN_API_KEY,
        'exchange rate')
    exchange_rate = result[1] / Decimal(config.TERMINAL_PRICE)
    return float(exchange_rate)


def create_invoice(fiat_amount):
    instantfiat_result = gocoin.create_invoice(
        fiat_amount,
        'GBP',
        config.GOCOIN_API_KEY,
        'terminals')
    return instantfiat_result

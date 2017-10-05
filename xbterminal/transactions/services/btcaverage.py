from decimal import Decimal

import requests


def get_exchange_rate(currency_name):
    ticker_url = 'https://api.bitcoinaverage.com/ticker/{0}/last'
    response = requests.get(ticker_url.format(currency_name))
    response.raise_for_status()
    return Decimal(response.text)

from decimal import Decimal

import requests


def get_exchange_rate(currency_code):
    ticker_url = "https://api.bitcoinaverage.com/ticker/{0}/last"
    try:
        response = requests.get(ticker_url.format(currency_code))
    except requests.exceptions.RequestException:
        return
    return Decimal(response.text)

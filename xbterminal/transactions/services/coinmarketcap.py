from decimal import Decimal

import requests

COINMARKETCAP_COIN_IDS = {
    'BTC': 'bitcoin',
    'TBTC': 'bitcoin',
    'DASH': 'dash',
    'TDASH': 'dash',
}


def get_exchange_rate(currency_name, coin_name):
    """
    https://coinmarketcap.com/api/
    """
    ticker_url = (
        'https://api.coinmarketcap.com'
        '/v1/ticker/{0}/?convert={1}')
    response = requests.get(ticker_url.format(
        COINMARKETCAP_COIN_IDS[coin_name],
        currency_name))
    response.raise_for_status()
    data = response.json()
    key = 'price_{}'.format(currency_name.lower())
    return Decimal(data[0][key])

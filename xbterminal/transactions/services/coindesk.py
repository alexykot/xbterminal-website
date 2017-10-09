from decimal import Decimal

import requests


def get_exchange_rate(currency_name):
    """
    http://www.coindesk.com/api/
    """
    api_url = 'https://api.coindesk.com/v1/bpi/currentprice/{0}.json'
    response = requests.get(api_url.format(currency_name))
    response.raise_for_status()
    data = response.json()
    return Decimal(data['bpi'][currency_name]['rate_float'])

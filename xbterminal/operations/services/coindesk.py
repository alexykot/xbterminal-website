from decimal import Decimal

import requests


def get_exchange_rate(currency_code):
    """
    http://www.coindesk.com/api/
    """
    api_url = 'https://api.coindesk.com/v1/bpi/currentprice/{0}.json'
    response = requests.get(api_url.format(currency_code))
    response.raise_for_status()
    data = response.json()
    return Decimal(data['bpi'][currency_code]['rate'])

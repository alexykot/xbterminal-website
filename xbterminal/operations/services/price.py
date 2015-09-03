from decimal import Decimal
import logging

import requests

logger = logging.getLogger(__name__)


def get_coindesk_rate(currency_code):
    """
    http://www.coindesk.com/api/
    """
    api_url = 'https://api.coindesk.com/v1/bpi/currentprice/{0}.json'
    response = requests.get(api_url.format(currency_code))
    response.raise_for_status()
    data = response.json()
    return Decimal(data['bpi'][currency_code]['rate'])


def get_bitcoinaverage_rate(currency_code):
    ticker_url = 'https://api.bitcoinaverage.com/ticker/{0}/last'
    response = requests.get(ticker_url.format(currency_code))
    response.raise_for_status()
    return Decimal(response.text)


def get_exchange_rate(currency_code):
    """
    Accepts:
        currency_code: 3-letter code
    Returns:
        exchange_rate: Decimal
    """
    try:
        return get_coindesk_rate(currency_code)
    except Exception as error:
        logger.exception(error)
        return get_bitcoinaverage_rate(currency_code)

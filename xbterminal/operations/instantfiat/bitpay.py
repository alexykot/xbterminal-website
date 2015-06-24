"""
https://bitpay.com/developers
"""
from decimal import Decimal
import logging
import re

import requests

from operations import BTC_DEC_PLACES

logger = logging.getLogger(__name__)


def create_invoice(fiat_amount, currency_code, api_key):
    invoice_url = "https://bitpay.com/api/invoice"
    payload = {
        'price': float(fiat_amount),
        'currency': currency_code,
        'transactionSpeed': "high",
    }
    try:
        response = requests.post(
            url=invoice_url,
            data=payload,
            auth=(api_key, ''))
        data = response.json()
    except (requests.exceptions.RequestException, ValueError):
        raise
    invoice_id = data['invoice_id']
    btc_amount = Decimal(data['amount']).quantize(BTC_DEC_PLACES)
    address = _get_address(invoice_id)
    logger.debug("bitpay invoice created")
    return invoice_id, btc_amount, address


def _get_address(invoice_id):
    invoice_address_url = "https://bitpay.com/invoice?id={0}".format(invoice_id)
    try:
        response = requests.get(invoice_address_url)
    except (requests.exceptions.RequestException, ValueError):
        raise
    match = re.search(r"bitcoin:(?P<addr>[13][a-zA-Z0-9]{26,33})\?",
                      response.text)
    return match.group('addr')


def is_invoice_paid(invoice_id, api_key):
    invoice_status_url = "https://bitpay.com/api/invoice/{0}".format(invoice_id)
    try:
        response = requests.get(
            url=invoice_status_url,
            auth=(api_key, ''))
        data = response.json()
    except (requests.exceptions.RequestException, ValueError):
        raise
    if data['status'] == 'paid':
        return True
    else:
        return False

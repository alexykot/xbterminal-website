"""
https://github.com/cryptopay-dev/cryptopay-api
"""
from decimal import Decimal
import json
import logging

import requests

import payment

logger = logging.getLogger(__name__)


def create_invoice(fiat_amount, currency_code, api_key, description):
    invoice_url = "https://cryptopay.me/api/v1/invoices/?api_key={0}".format(api_key)
    payload = {
        'price': float(fiat_amount),
        'currency': currency,
        'description': description,
    }
    try:
        response = requests.post(
            url=invoice_url,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(payload))
        data = response.json()
    except (requests.exceptions.RequestException, ValueError):
        raise
    invoice_id = data['uuid']
    btc_amount = (Decimal(data['btc_price']).quantize(payment.BTC_DEC_PLACES) +
                  Decimal('0.00000001'))  # Adding one satoshi to avoid rounding issues
    address = data['btc_address'],
    logger.debug("cryptopay invoice created")
    return invoice_id, btc_amount, address


def is_invoice_paid(invoice_id, api_key):
    invoice_status_url = "https://cryptopay.me/api/v1/invoices/{0}?api_key={1}".\
        format(invoice_id, api_key=api_key)
    try:
        response = requests.get(
            url=invoice_status_url,
            headers={'Content-Type': 'application/json'})
        data = response.json()
    except (requests.exceptions.RequestException, ValueError):
        raise
    if data['status'] == 'paid':
        return True
    else:
        return False

"""
http://docs.gocoinapi.apiary.io/#invoices
"""
from decimal import Decimal
import json
import logging

import requests
from requests.auth import AuthBase

import payment

logger = logging.getLogger(__name__)


class BearerAuth(AuthBase):
    def __init__(self, access_token):
        self.access_token = access_token

    def __call__(self, req):
        req.headers['Authorization'] = "Bearer {0}".format(self.access_token)
        return req


def create_invoice(fiat_amount, currency_code, api_key, description):
    merchant_id, api_key = api_key.split(':')
    invoice_url = "https://api.gocoin.com/api/v1/merchants/{0}/invoices".\
        format(merchant_id)
    payload = {
        'price_currency': 'BTC',
        'base_price': float(fiat_amount),
        'base_price_currency': currency_code,
        'confirmations_required': 0,
    }
    try:
        response = requests.post(
            url=invoice_url,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(payload),
            auth=BearerAuth(api_key))
        data = response.json()
    except (requests.exceptions.RequestException, ValueError):
        raise
    invoice_id = data['id'],
    btc_amount = Decimal(data['price']).quantize(payment.BTC_DEC_PLACES),
    address = data['payment_address'],
    logger.debug('gocoin invoice created')
    return invoice_id, btc_amount, address


def is_invoice_paid(invoice_id, api_key):
    merchant_id, api_key = api_key.split(':')
    invoice_status_url = "https://api.gocoin.com/api/v1/invoices/{0}".\
        format(invoice_id)
    try:
        response = requests.get(
            url=invoice_status_url,
            headers={'Content-Type': 'application/json'},
            auth=BearerAuth(api_key))
        data = response.json()
    except (requests.exceptions.RequestException, ValueError):
        raise
    if data['status'] == 'paid':
        return True
    else:
        return False

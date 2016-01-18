"""
https://github.com/cryptopay-dev/cryptopay-api
"""
from decimal import Decimal
import json
import logging

import requests

from operations import BTC_DEC_PLACES
from operations.exceptions import InstantFiatError

logger = logging.getLogger(__name__)


def create_invoice(fiat_amount, currency_code, api_key, description):
    invoice_url = "https://cryptopay.me/api/v1/invoices"
    payload = {
        'api_key': api_key,
        'price': float(fiat_amount),
        'currency': currency_code,
        'confirmations_count': 0,
        'description': description,
    }
    response = requests.post(
        url=invoice_url,
        headers={'Content-Type': 'application/json'},
        data=json.dumps(payload))
    try:
        response.raise_for_status()
        data = response.json()
        invoice_id = data['uuid']
        btc_amount = Decimal(data['btc_price']).quantize(BTC_DEC_PLACES)
        address = data['btc_address']
    except:
        raise InstantFiatError(response.text)
    else:
        logger.debug('cryptopay invoice created')
        return invoice_id, btc_amount, address


def is_invoice_paid(invoice_id, api_key):
    invoice_status_url = "https://cryptopay.me/api/v1/invoices/{0}?api_key={1}".\
        format(invoice_id, api_key)
    try:
        response = requests.get(
            url=invoice_status_url,
            headers={'Content-Type': 'application/json'})
        try:
            response.raise_for_status()
            data = response.json()
            assert 'status' in data
        except:
            raise InstantFiatError(response.text)
    except Exception as error:
        # Log exception, do not raise
        logger.exception(error)
        return False
    if data['status'] in ['paid', 'confirmed']:
        return True
    else:
        return False

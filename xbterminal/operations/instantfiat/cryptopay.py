"""
https://developers.cryptopay.me/
"""
from decimal import Decimal
import json
import logging

import requests

from operations import BTC_DEC_PLACES
from operations.exceptions import (
    InstantFiatError,
    CryptoPayUserAlreadyExists)

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


def create_merchant(first_name, last_name, email, api_key):
    """
    Creates CryptoPay user with random password
    Accepts:
        first_name, last_name, email: merchant info
        api_key: CryptoPay API key with access to users API
    Returns:
        merchant id, merchant api key
    """
    api_url = 'https://cryptopay.me/api/v2/users'
    payload = {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'send_welcome_email': False,
    }
    assert api_key
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': api_key,
    }
    response = requests.post(
        api_url,
        data=json.dumps(payload),
        headers=headers)
    data = response.json()
    if response.status_code == 201:
        return data['id'], data['apikey']
    else:
        if data['email'] == ['has already been taken']:
            raise CryptoPayUserAlreadyExists
        else:
            response.raise_for_status()
            raise Exception


def set_password(user_id, password, api_key):
    """
    Set new password for CryptoPay user
    Accepts:
        user_id: CryptoPay user ID
        password: new password
        api_key: CryptoPay API key with access to users API
    """
    api_url = 'https://cryptopay.me/api/v2/users/{user_id}/password'
    payload = {
        'password': password,
    }
    assert api_key
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': api_key,
    }
    response = requests.post(
        api_url.format(user_id=user_id),
        data=json.dumps(payload),
        headers=headers)
    try:
        response.raise_for_status()
        data = response.json()
        assert data['status'] == 'success'
    except:
        raise InstantFiatError(response.text)

"""
https://developers.cryptopay.me/
"""
from decimal import Decimal, ROUND_HALF_DOWN
import json
import logging

import requests

from operations import BTC_DEC_PLACES
from operations.exceptions import (
    InstantFiatError,
    CryptoPayUserAlreadyExists,
    CryptoPayInvalidAPIKey,
    InsufficientFunds)
from website.utils.files import encode_base64

logger = logging.getLogger(__name__)

DEFAULT_CURRENCIES = ['GBP', 'USD', 'EUR']


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


def get_final_amount(amount):
    """
    Calculate invoice fee
    """
    fee_percent = Decimal('0.01')
    quanta = Decimal('0.00')
    return (amount * (1 - fee_percent)).quantize(
        quanta,
        rounding=ROUND_HALF_DOWN)


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
        merchant_id = data['id']
        return merchant_id
    else:
        if data.get('email') == ['has already been taken']:
            raise CryptoPayUserAlreadyExists
        else:
            response.raise_for_status()
            raise Exception


def get_merchant(user_id, api_key):
    """
    Accepts:
        user_id: CryptoPay user ID
        api_key: CryptoPay API key with access to users API
    """
    api_url = 'https://cryptopay.me/api/v2/users/{user_id}'
    assert api_key
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': api_key,
    }
    response = requests.get(
        api_url.format(user_id=user_id),
        headers=headers)
    response.raise_for_status()
    data = response.json()
    return data


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


def upload_documents(user_id, documents, api_key):
    """
    Accepts:
        user_id: CryptoPay user ID
        documents: list of file-like objects
        api_key: CryptoPay API key with access to users API
    Returns:
        id: upload ID
    """
    api_url = 'https://cryptopay.me/api/v2/users/{user_id}/documents'
    payload = {
        'id_document_frontside': encode_base64(documents[0]),
        'id_document_backside': encode_base64(documents[1]),
        'residence_document': encode_base64(documents[2]),
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
    response.raise_for_status()
    data = response.json()
    return data['id']


def list_accounts(api_key):
    """
    Accepts:
        api_key: merchant's API key
    """
    api_url = 'https://cryptopay.me/api/v2/accounts'
    assert api_key
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': api_key,
    }
    response = requests.get(api_url, headers=headers)
    if response.status_code == 403:
        raise CryptoPayInvalidAPIKey
    response.raise_for_status()
    data = response.json()
    return data


def list_transactions(account_id, api_key):
    """
    Accepts:
        account_id: CryptoPay account ID
        api_key: merchant's API key
    """
    api_url = 'https://cryptopay.me/api/v2/accounts/{account_id}/transactions'
    assert api_key
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': api_key,
    }
    response = requests.get(
        api_url.format(account_id=account_id),
        headers=headers)
    response.raise_for_status()
    data = response.json()
    return data


def send_transaction(account_id, currency_name, fiat_amount, destination, api_key):
    """
    Send bitcoins from CryptoPay account
    Accepts:
        account_id: CryptoPay account ID
        currency_name: currency code
        fiat_amount: fiat amount, Decimal
        destination: bitcoin address
        api_key: merchant's API key
    Returns:
        transfer_id: transfer ID
        reference: transfer reference
        btc_amount: bitcoin amount, Decimal
    """
    api_url = 'https://cryptopay.me/api/v2/bitcoin_transfers'
    payload = {
        'amount_currency': currency_name,
        'amount': float(fiat_amount),
        'account': account_id,
        'address': destination,
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
    if response.status_code == 201:
        data = response.json()
        transfer_id = data['id']
        reference = data['cryptopay_reference']
        btc_amount = Decimal(data['amount']).quantize(BTC_DEC_PLACES)
        return transfer_id, reference, btc_amount
    elif response.status_code == 422:
        data = response.json()
        if data['errors'] == ['Amount balance is not enough.']:
            raise InsufficientFunds
    raise InstantFiatError(response.text)


def get_transfer(transfer_id, api_key):
    """
    Get details of bitcoin transfer
    Accepts:
        transfer_id: CryptoPay transfer ID
        api_key: merchant's API key
    """
    api_url = 'https://cryptopay.me/api/v2/bitcoin_transfers/{transfer_id}'
    assert api_key
    headers = {
        'Content-Type': 'application/json',
        'X-Api-Key': api_key,
    }
    response = requests.get(
        api_url.format(transfer_id=transfer_id),
        headers=headers)
    response.raise_for_status()
    data = response.json()
    return data


def check_transfer(transfer_id, api_key):
    """
    Check status of bitcoin transfer
    Accepts:
        transfer_id: CryptoPay transfer ID
        api_key: merchant's API key
    Returns:
        is_completed: boolean
        tx_hash: bitcoin transaction ID
    """
    try:
        result = get_transfer(transfer_id, api_key)
        is_completed = (result['status'] == 'completed')
        tx_hash = result['tx_hash']
    except Exception:
        raise InstantFiatError
    else:
        return is_completed, tx_hash

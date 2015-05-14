"""
http://docs.gocoinapi.apiary.io/#invoices
"""
from decimal import Decimal
import json
import logging

import requests
from requests.auth import AuthBase

import payment
from payment.exceptions import InstantFiatError

logger = logging.getLogger(__name__)


class BearerAuth(AuthBase):
    def __init__(self, access_token):
        self.access_token = access_token

    def __call__(self, req):
        req.headers['Authorization'] = "Bearer {0}".format(self.access_token)
        return req


def create_invoice(fiat_amount, currency_code, api_key, merchant_id):
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
    except requests.exceptions.RequestException:
        raise
    except ValueError:
        raise InstantFiatError(response.text)
    if 'errors' in data:
        raise InstantFiatError(str(data))
    invoice_id = data['id']
    btc_amount = Decimal(data['price']).quantize(payment.BTC_DEC_PLACES)
    address = data['payment_address']
    logger.debug('gocoin - invoice created')
    return invoice_id, btc_amount, address


def is_invoice_paid(invoice_id, api_key, merchant_id):
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


class GoCoinNameAlreadyTaken(InstantFiatError):

    message = 'Merchant name has already been taken'


def create_merchant(merchant, api_key):
    """
    Accepts:
        merchant: MerchantAccount instance
        api_key: GoCoin token with access to merchant API
    Returns:
        id: GoCoin merchant id
    """
    merchants_url = "https://api.gocoin.com/api/v1/merchants"
    payload = {
        'name': merchant.company_name,
        'address_1': merchant.business_address,
        'address_2': merchant.business_address1,
        'city': merchant.town,
        'region': merchant.county,
        'country_code': merchant.country.code,
        'postal_code': merchant.post_code,
        'contact_name': merchant.contact_name,
        'contact_email': merchant.contact_email,
        'phone': merchant.contact_phone,
    }
    try:
        response = requests.post(
            merchants_url,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(payload),
            auth=BearerAuth(api_key))
        data = response.json()
    except requests.exceptions.RequestException:
        raise
    except ValueError:
        raise InstantFiatError(response.text)
    if 'errors' in data:
        if 'has already been taken' in data['errors'].get('name', []):
            raise GoCoinNameAlreadyTaken()
        raise InstantFiatError(str(data))
    merchant_id = data['id']
    logger.info('gocoin - created merchant {0}'.format(merchant_id))
    return merchant_id


def update_merchant(merchant, api_key):
    """
    Accepts:
        merchant: MerchantAccount instance
        api_key: GoCoin token with access to merchant API
    """
    merchant_url = "https://api.gocoin.com/api/v1/merchants/{0}".\
        format(merchant.gocoin_merchant_id)
    payload = {
        'name': merchant.company_name,
        'address_1': merchant.business_address,
        'address_2': merchant.business_address1,
        'city': merchant.town,
        'region': merchant.county,
        'country_code': merchant.country.code,
        'postal_code': merchant.post_code,
        'contact_name': merchant.contact_name,
        'contact_email': merchant.contact_email,
        'phone': merchant.contact_phone,
    }
    try:
        response = requests.patch(
            merchant_url,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(payload),
            auth=BearerAuth(api_key))
        data = response.json()
    except requests.exceptions.RequestException:
        raise
    except ValueError:
        raise InstantFiatError(response.text)
    if 'errors' in data:
        if 'has already been taken' in data['errors'].get('name', []):
            raise GoCoinNameAlreadyTaken()
        raise InstantFiatError(str(data))
    logger.info('gocoin - updated merchant {0}'.format(data['id']))


def get_merchants(merchant_id, api_key):
    """
    Lists the child merchants of an existing merchant
    """
    merchants_url = "https://api.gocoin.com/api/v1/merchants/{0}/children".\
        format(merchant_id)
    try:
        response = requests.get(
            merchants_url,
            headers={'Content-Type': 'application/json'},
            auth=BearerAuth(api_key))
        data = response.json()
    except requests.exceptions.RequestException:
        raise
    except ValueError:
        raise InstantFiatError(response.text)
    if 'errors' in data:
        raise InstantFiatError(str(data))
    return [merchant['id'] for merchant in data]


def upload_kyc_document(document, api_key):
    """
    Accepts:
        document: KYCDocument instance
        api_key: GoCoin token with access to merchant API
    """
    documents_url = "https://api.gocoin.com/api/v1/merchants/{0}/kyc_documents".\
        format(document.merchant.gocoin_merchant_id)
    try:
        response = requests.post(
            documents_url,
            data={'type': document.get_document_type_display()},
            files={'image': document.file},
            auth=BearerAuth(api_key))
        data = response.json()
    except requests.exceptions.RequestException:
        raise
    except ValueError:
        raise InstantFiatError(response.text)
    if 'errors' in data:
        raise InstantFiatError(str(data))
    return data['id']


def check_kyc_documents(merchant, api_key):
    """
    Accepts:
        merchant: MerchantAccount instance
        api_key: GoCoin token with access to merchant API
    Returns:
        list of pending documents and their statuses
    """
    documents_url = "https://api.gocoin.com/api/v1/merchants/{0}/kyc_documents".\
        format(merchant.gocoin_merchant_id)
    try:
        response = requests.get(
            documents_url,
            auth=BearerAuth(api_key))
        data = response.json()
    except requests.exceptions.RequestException:
        raise
    except ValueError:
        raise InstantFiatError(response.text)
    if 'errors' in data:
        raise InstantFiatError(str(data))
    return data

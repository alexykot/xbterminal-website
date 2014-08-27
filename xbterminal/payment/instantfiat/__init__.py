"""
Instantfiat
"""
import importlib


def create_invoice(service_name, api_key,
                   fiat_amount, currency_code, description=""):
    """
    Create invoice
    Accepts:
        fiat_amount: Decimal
        currency_code: ISO 4217 code
        service_name: string
        api_key: string
        description: string (optional)
    """
    instantfiat_mod = importlib.import_module(
        '.' + service_name, 'payment.instantfiat')
    invoice_id, btc_amount, address = instantfiat_mod.create_invoice(
        fiat_amount, currency_code, api_key, description)
    result = {
        'instantfiat_invoice_id': invoice_id,
        'instantfiat_address': address,
        'instantfiat_btc_amount': btc_amount,
    }
    return result


def is_invoice_paid(service_name, api_key, invoice_id):
    """
    Check payment
    Accepts:
        service_name: string
        api_key: string
        invoice_id: string
    """
    instantfiat_mod = importlib.import_module(
        '.' + service_name, 'payment.instantfiat')
    result = instantfiat_mod.is_invoice_paid(invoice_id, api_key)
    return result

"""
Instantfiat
"""
from constance import config

from payment.instantfiat import bitpay, cryptopay, gocoin


def create_invoice(merchant, fiat_amount):
    """
    Create invoice
    Accepts:
        merchant: MerchantAccount instance
        fiat_amount: Decimal
    """
    service_name = merchant.payment_processor
    if service_name == 'bitpay':
        invoice_id, btc_amount, address = bitpay.create_invoice(
            fiat_amount,
            merchant.currency.name,
            merchant.api_key)
    elif service_name == 'cryptopay':
        invoice_id, btc_amount, address = cryptopay.create_invoice(
            fiat_amount,
            merchant.currency.name,
            merchant.api_key,
            "Payment to {0}".format(merchant.company_name))
    elif service_name == 'gocoin':
        invoice_id, btc_amount, address = gocoin.create_invoice(
            fiat_amount,
            merchant.currency.name,
            merchant.api_key or config.GOCOIN_API_KEY,
            merchant.gocoin_merchant_id)
    return {
        'instantfiat_invoice_id': invoice_id,
        'instantfiat_btc_amount': btc_amount,
        'instantfiat_address': address,
    }


def is_invoice_paid(merchant, invoice_id):
    """
    Check payment
    Accepts:
        merchant: MerchantAccount instance
        invoice_id: string
    """
    service_name = merchant.payment_processor
    if service_name == 'bitpay':
        result = bitpay.is_invoice_paid(invoice_id, merchant.api_key)
    elif service_name == 'cryptopay':
        result = cryptopay.is_invoice_paid(invoice_id, merchant.api_key)
    elif service_name == 'gocoin':
        result = gocoin.is_invoice_paid(
            invoice_id,
            merchant.api_key or config.GOCOIN_API_KEY,
            merchant.gocoin_merchant_id)
    return result

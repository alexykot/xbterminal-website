"""
Instantfiat
"""
from website.models import INSTANTFIAT_PROVIDERS
from operations.instantfiat import cryptopay


def create_invoice(account, fiat_amount):
    """
    Create invoice
    Accepts:
        account: Account instance
        fiat_amount: Decimal
    """
    if account.merchant.instantfiat_provider == INSTANTFIAT_PROVIDERS.CRYPTOPAY:
        invoice_id, btc_amount, address = cryptopay.create_invoice(
            fiat_amount,
            account.currency.name,
            account.merchant.instantfiat_api_key,
            'Payment to {0}'.format(account.merchant.company_name))
    else:
        raise AssertionError
    return invoice_id, btc_amount, address


def is_invoice_paid(account, invoice_id):
    """
    Check payment
    Accepts:
        account: Account instance
        invoice_id: string
    """
    if account.merchant.instantfiat_provider == INSTANTFIAT_PROVIDERS.CRYPTOPAY:
        result = cryptopay.is_invoice_paid(
            invoice_id,
            account.merchant.instantfiat_api_key)
    else:
        raise AssertionError
    return result


def send_transaction(account, fiat_amount, destination):
    """
    Send bitcoin transaction from instantfiat account
    Accepts:
        account: Account instance
        fiat_amount: Decimal
        destination: bitcoin address, string
    """
    if account.merchant.instantfiat_provider == INSTANTFIAT_PROVIDERS.CRYPTOPAY:
        transfer_id, reference, btc_amount = cryptopay.send_transaction(
            account.instantfiat_account_id,
            account.currency.name,
            fiat_amount,
            destination,
            account.merchant.instantfiat_api_key)
        return transfer_id, reference, btc_amount
    else:
        raise AssertionError


def check_transfer(account, transfer_id):
    """
    Check transfer status
    Accepts:
        account: Account instance
        transfer_id: string
    """
    if account.merchant.instantfiat_provider == INSTANTFIAT_PROVIDERS.CRYPTOPAY:
        return cryptopay.check_transfer(
            transfer_id,
            account.merchant.instantfiat_api_key)
    else:
        raise AssertionError

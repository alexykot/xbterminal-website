import re

import bitcoin
from bitcoin.wallet import CBitcoinAddress

from django.core.exceptions import ValidationError


def validate_percent(value):
    if value > 100 or value < 0:
        raise ValidationError(u'%s is not an valid percent' % value)


def validate_transaction(value):
    if re.match(r"^[0-9A-Fa-f]{64}$", value) is None:
        raise ValidationError('Invalid Bitcoin transaction.')


def validate_phone(value):
    if re.match(r"^[0-9\s\-+().]{5,20}$", value) is None:
        raise ValidationError('Please enter a valid phone number.')


def validate_post_code(value):
    if re.match(r"^[a-zA-Z0-9\s\-+]{2,10}$", value) is None:
        raise ValidationError('Please enter a valid post code.')


def _validate_bitcoin_address(address, network):
    """
    Validate address
    Accepts:
        address: string
        network: mainnet or testnet
    Returns:
        error: error message
    """
    try:
        address = CBitcoinAddress(address)
    except:
        return "Invalid bitcoin address."
    if network is None:
        return None
    elif network == "mainnet":
        prefixes = bitcoin.MainParams.BASE58_PREFIXES.values()
    elif network == "testnet":
        prefixes = bitcoin.TestNetParams.BASE58_PREFIXES.values()
    if address.nVersion not in prefixes:
        return "Invalid address for network {0}.".format(network)


def validate_bitcoin_address(address, network=None):
    error_message = _validate_bitcoin_address(address, network)
    if error_message is not None:
        raise ValidationError(error_message)

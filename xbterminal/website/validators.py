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


def validate_bitcoin_address(address, network=None):
    try:
        address = CBitcoinAddress(address)
    except:
        raise ValidationError("Invalid bitcoin address.")
    if network is None:
        return
    elif network == "mainnet":
        prefixes = bitcoin.MainParams.BASE58_PREFIXES.values()
    elif network == "testnet":
        prefixes = bitcoin.TestNetParams.BASE58_PREFIXES.values()
    if address.nVersion not in prefixes:
        raise ValidationError("Invalid address for network {0}.".format(network))

import re

from django.core.exceptions import ValidationError

from api.utils.crypto import load_public_key
from operations import blockchain


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
    error_message = blockchain.validate_bitcoin_address(address, network)
    if error_message is not None:
        raise ValidationError(error_message)


def validate_public_key(value):
    try:
        load_public_key(value)
    except:
        raise ValidationError('Invalid API public key.')

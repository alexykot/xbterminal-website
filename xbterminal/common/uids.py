import random
import uuid

from bitcoin import base58
from pycoin.encoding import b2a_base58


def generate_b58_uid_(length):
    bts = uuid.uuid4().bytes
    return base58.encode(bts)[:length]


def generate_b58_uid(length):
    bts = uuid.uuid4().bytes
    return b2a_base58(bts)[:length]


def generate_alphanumeric_code(length):
    """
    Generate simple human-readable code
    """
    chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZ'
    code = ''.join(random.sample(chars, length))
    return code

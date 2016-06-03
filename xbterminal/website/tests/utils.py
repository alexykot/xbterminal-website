import random

import bitcoin
from bitcoin.core import Hash160
from bitcoin.wallet import CBitcoinAddress


def generate_bitcoin_address(network='mainnet'):
    """
    Generate random bitcoin address (for testing)
    """
    randbytes = str(random.random()).encode('utf-8')
    bitcoin.SelectParams(network)
    address_prefix = bitcoin.params.BASE58_PREFIXES['PUBKEY_ADDR']
    pubkey_hash = Hash160(randbytes)
    address = CBitcoinAddress.from_bytes(pubkey_hash, address_prefix)
    return str(address)

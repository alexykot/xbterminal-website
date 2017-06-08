import binascii

from pycoin.key.BIP32Node import BIP32Node
from pycoin.tx.pay_to import script_obj_from_script


def create_master_key(currency_code, secret):
    return BIP32Node.from_master_secret(secret, netcode=currency_code)


def create_wallet_key(master_key, path, as_private=False):
    key = master_key.subkey_for_path(path)
    return key.hwif(as_private=as_private)


def generate_p2pkh_script(parent_key, path, as_address=True):
    """
    Generate BTC/LTC P2PKH script or address
    Accepts:
        parent_key: serialized parent private key
        path: relative path
        as_address: boolean
    Returns:
        address or script, string
    """
    parent_key = BIP32Node.from_hwif(parent_key)
    child_key = parent_key.subkey_for_path(path)
    address = child_key.address()
    if as_address:
        return address
    else:
        script = script_obj_from_script(address).script()
        return binascii.hexlify(script).decode()

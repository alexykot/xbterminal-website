import binascii

from pycoin.key.BIP32Node import BIP32Node
from pycoin.tx.pay_to import script_obj_from_script


def create_master_key(secret):
    return BIP32Node.from_master_secret(secret)


def create_wallet_key(master_key, netcode, path, as_private=False):
    key = master_key.subkey_for_path(path)
    key._netcode = netcode
    return key.hwif(as_private=as_private)


def derive_key(parent_key, path):
    """
    Accepts:
        parent_key: extended key in WIF, string
        path: BIP32 path, string
    Returns:
        BIP32Node instance
    """
    parent_key = BIP32Node.from_hwif(parent_key)
    child_key = parent_key.subkey_for_path(path)
    return child_key


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
    child_key = derive_key(parent_key, path)
    address = child_key.address()
    if as_address:
        return address
    else:
        script = script_obj_from_script(address).script()
        return binascii.hexlify(script).decode()

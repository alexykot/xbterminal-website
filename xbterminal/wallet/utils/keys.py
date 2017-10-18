import binascii

from pycoin.encoding import EncodingError
from pycoin.key.BIP32Node import BIP32Node
from pycoin.tx.pay_to import script_obj_from_script


def deserialize_key(key_wif):
    return BIP32Node.from_hwif(key_wif)


def create_master_key(secret):
    if isinstance(secret, int):
        secret = str(secret)
    return BIP32Node.from_master_secret(secret)


def create_wallet_key(master_key, purpose, netcode, bip44_type):
    key = master_key.\
        subkey(purpose, is_hardened=True).\
        subkey(bip44_type, is_hardened=True)
    key._netcode = netcode
    return key.hwif(as_private=True)


def is_valid_master_key(master_key_wif):
    """
    Accepts:
        master_key_wif: master key in WIF
    Returns:
        True of False
    """
    try:
        master_key = BIP32Node.from_hwif(master_key_wif)
    except EncodingError:
        return False
    if not master_key.is_private():
        return False
    if master_key.tree_depth() != 0:
        return False
    if master_key.child_index() != 0:
        return False
    return True


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

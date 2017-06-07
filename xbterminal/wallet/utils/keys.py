from pycoin.key.BIP32Node import BIP32Node


def create_master_key(currency_code, secret):
    return BIP32Node.from_master_secret(secret, netcode=currency_code)


def create_wallet_key(master_key, path, as_private=False):
    key = master_key.subkey_for_path(path)
    return key.hwif(as_private=as_private)

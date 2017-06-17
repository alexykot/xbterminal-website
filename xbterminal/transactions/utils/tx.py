import binascii

from bitcoin.core import COIN, CTransaction
from pycoin.tx.Spendable import Spendable
from pycoin.tx.Tx import Tx
from pycoin.tx.TxOut import TxOut
from pycoin.tx.pay_to import build_hash160_lookup
from pycoin.ui import standard_tx_out_script


def create_tx(tx_inputs, tx_outputs):
    """
    Accepts:
        tx_inputs: list of dicts containing inputs data
        tx_outputs: dict containing addresses and corresponding amounts
    Returns:
        signed transaction (Tx instance)
    """
    spendables = []
    private_keys = []
    for tx_input in tx_inputs:
        spendables.append(Spendable.from_dict({
            'tx_hash_hex': tx_input['txid'],
            'tx_out_index': tx_input['vout'],
            'coin_value': int(tx_input['amount'] * COIN),
            'script_hex': tx_input['scriptPubKey'],
        }))
        private_keys.append(tx_input['private_key'])
    txs_in = [spendable.tx_in() for spendable in spendables]
    txs_out = []
    for address, amount in tx_outputs.items():
        script = standard_tx_out_script(address)
        out = TxOut(int(amount * COIN), script)
        txs_out.append(out)
    tx = Tx(version=1, txs_in=txs_in, txs_out=txs_out, lock_time=0)
    tx.set_unspents(spendables)
    hash160_lookup = build_hash160_lookup(
        [key.secret_exponent() for key in private_keys])
    tx.sign(hash160_lookup)
    if tx.bad_signature_count() != 0:
        raise ValueError('Invalid signature')
    return tx


def convert_tx(tx):
    """
    Convert pycoin Tx object to bitcoinlib CTransaction
    """
    return CTransaction.deserialize(binascii.unhexlify(tx.as_hex()))


def create_tx_(tx_inputs, tx_outputs):
    return convert_tx(create_tx(tx_inputs, tx_outputs))
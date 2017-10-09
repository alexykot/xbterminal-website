from decimal import Decimal

from pycoin.tx.Spendable import Spendable
from pycoin.tx.Tx import Tx
from pycoin.tx.TxOut import TxOut
from pycoin.tx.pay_to import build_hash160_lookup
from pycoin.ui import standard_tx_out_script

from transactions.constants import BTC_MIN_OUTPUT, BTC_DEC_PLACES
from transactions.exceptions import DustOutput


def to_units(amount):
    return int(amount * 10 ** 8)


def from_units(amount):
    amount = Decimal(amount) / 10 ** 8
    return amount.quantize(BTC_DEC_PLACES)


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
            'coin_value': to_units(tx_input['amount']),
            'script_hex': tx_input['scriptPubKey'],
        }))
        private_keys.append(tx_input['private_key'])
    txs_in = [spendable.tx_in() for spendable in spendables]
    txs_out = []
    for address, amount in tx_outputs.items():
        if amount < BTC_MIN_OUTPUT:
            raise DustOutput
        script = standard_tx_out_script(address)
        out = TxOut(to_units(amount), script)
        txs_out.append(out)
    tx = Tx(version=1, txs_in=txs_in, txs_out=txs_out, lock_time=0)
    tx.set_unspents(spendables)
    hash160_lookup = build_hash160_lookup(
        [key.secret_exponent() for key in private_keys])
    tx.sign(hash160_lookup)
    if tx.bad_signature_count() != 0:
        raise ValueError('Invalid signature')
    return tx

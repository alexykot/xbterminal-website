from decimal import Decimal
import urllib
from cStringIO import StringIO

import bitcoin
import bitcoin.rpc
from bitcoin.base58 import CBase58Data
from bitcoin.core import COIN, x, lx, b2lx, CTransaction, COutPoint
from bitcoin.core.serialize import Hash
from bitcoin.wallet import CBitcoinAddress

from django.conf import settings
from constance import config

from operations import BTC_DEC_PLACES
from operations import exceptions


class BlockChain(object):

    def __init__(self, network):
        self.network = network
        # TODO: don't set global params
        bitcoin.SelectParams(self.network)
        config = settings.BITCOIND_SERVERS[self.network]
        service_url = "http://{user}:{password}@{host}:{port}".format(
            user=config['USER'],
            password=config['PASSWORD'],
            host=config['HOST'],
            port=config.get('PORT', bitcoin.params.RPC_PORT))
        self._proxy = bitcoin.rpc.Proxy(service_url)

    def get_new_address(self):
        """
        Returns:
            address: CBitcoinAddress
        """
        address = self._proxy.getnewaddress()
        return address

    def get_balance(self, minconf=1):
        """
        Accepts:
            minconf: only include transactions confirmed at least this many times.
        Returns:
            balance: BTC amount (Decimal)
        """
        balance = self._proxy.getbalance(minconf=minconf)
        return Decimal(balance).quantize(BTC_DEC_PLACES) / COIN

    def get_address_balance(self, address):
        """
        Accepts:
            address: CBitcoinAddress
        Returns:
            balance: BTC amount (Decimal)
        """
        txouts = self._proxy.listunspent(minconf=0, addrs=[str(address)])
        balance = Decimal(0)
        for out in txouts:
            balance += Decimal(out['amount']) / COIN
        return balance.quantize(BTC_DEC_PLACES)

    def get_unspent_outputs(self, address, minconf=0):
        """
        Accepts:
            address: CBitcoinAddress
            minconf: only include transactions confirmed at least this many times
        Returns:
            txouts: list of dicts
        """
        txouts = self._proxy.listunspent(minconf=minconf, addrs=[address])
        for out in txouts:
            out['amount'] = Decimal(out['amount']) / COIN
        return txouts

    def get_unspent_transactions(self, address):
        """
        Accepts:
            address: CBitcoinAddress
        Returns:
            transactions: list of CTransaction
        """
        txouts = self._proxy.listunspent(minconf=0, addrs=[address])
        transactions = []
        for out in txouts:
            txid = b2lx(out['outpoint'].hash)
            transactions.append(self.get_raw_transaction(txid))
        return transactions

    def get_raw_transaction(self, transaction_id):
        """
        Accepts:
            transaction_id: hex string
        Returns:
            transaction: CTransaction
        """
        transaction = self._proxy.getrawtransaction(lx(transaction_id))
        return transaction

    def get_tx_inputs(self, transaction):
        """
        Return transaction inputs
        Accepts:
            transaction: CTransaction
        Returns:
            list of inputs (Decimal amount, CBitcoinAddress)
        """
        inputs = []
        for txin in transaction.vin:
            input_tx = self._proxy.getrawtransaction(txin.prevout.hash)
            input_tx_out = input_tx.vout[txin.prevout.n]
            amount = Decimal(input_tx_out.nValue) / COIN
            address = CBitcoinAddress.from_scriptPubKey(input_tx_out.scriptPubKey)
            inputs.append({'amount': amount, 'address': address})
        return inputs

    def get_tx_outputs(self, transaction):
        """
        Return transaction outputs
        Accepts:
            transaction: CTransaction
        Returns:
            outputs: list of outputs
        """
        outputs = []
        for txout in transaction.vout:
            amount = Decimal(txout.nValue) / COIN
            address = CBitcoinAddress.from_scriptPubKey(txout.scriptPubKey)
            outputs.append({'amount': amount, 'address': address})
        return outputs

    def create_raw_transaction(self, inputs, outputs):
        """
        Accepts:
            inputs: list of COutPoint
            outputs: {address: amount, ...}
        Returns:
            transaction: CTransaction
        """
        # Parse inputs
        inputs_ = []
        for outpoint in inputs:
            inputs_.append({
                'txid': b2lx(outpoint.hash),  # b2lx, not b2x
                'vout': outpoint.n,
            })
        # Convert decimal to float, filter outputs
        outputs_ = {}
        for address, amount in outputs.items():
            if amount > 0:
                outputs_[address] = float(amount)
        assert len(outputs_) > 0
        # Create transaction
        transaction_hex = self._proxy._call(
            'createrawtransaction', inputs_, outputs_)
        transaction = CTransaction.deserialize(x(transaction_hex))
        return transaction

    def sign_raw_transaction(self, transaction):
        """
        Accepts:
            transaction: CTransaction
        Returns:
            transaction_signed: CTransaction
        """
        result = self._proxy.signrawtransaction(transaction)
        if result.get('complete') != 1:
            raise exceptions.InvalidTransaction(get_txid(transaction))
        return result['tx']

    def send_raw_transaction(self, transaction):
        """
        Accepts:
            transaction: CTransaction
        Returns:
            transaction_id: hex string
        """
        transaction_id = self._proxy.sendrawtransaction(transaction)
        return b2lx(transaction_id)

    def is_tx_confirmed(self, transaction_id, minconf=1):
        """
        Accepts:
            transaction_id: hex string
        Returns:
            True or False
        """
        tx_info = self._proxy.gettransaction(lx(transaction_id))
        if tx_info['confirmations'] >= minconf:
            return True
        return False

    def get_tx_fee(self, n_inputs, n_outputs,
                   n_blocks=config.TX_EXPECTED_CONFIRM):
        """
        Accepts:
            n_inputs: number of inputs
            n_outputs: number of outputs
            n_blocks: the maximum number of blocks a transaction
                should have to wait before it is predicted
                to be included in a block
        Returns:
            fee
        """
        fee_per_kb = self._proxy.call('estimatefee', n_blocks)
        if fee_per_kb == -1:
            fee_per_kb = config.TX_DEFAULT_FEE
        return get_tx_fee(n_inputs, n_outputs, fee_per_kb)


def construct_bitcoin_uri(address, amount_btc, name, *request_urls):
    """
    https://github.com/bitcoin/bips/blob/master/bip-0021.mediawiki
    Accepts:
        address: CBitcoinAddress
        amount_btc: Decimal
        name: merchant name
        request_urls: urls, strings
    Returns:
        bitcoin uri: string
    """
    amount_btc = amount_btc.quantize(Decimal('0.00000000'))
    uri = "bitcoin:{0}?amount={1}&label={2}&message={3}".format(
        str(address),
        str(amount_btc),
        urllib.quote(name),
        urllib.quote(name))
    for idx, request_url in enumerate(request_urls):
        param_name = "r" if idx == 0 else "r{0}".format(idx)
        uri += "&{0}={1}".format(param_name, request_url)
    return uri


def get_txid(transaction):
    """
    Calculate transaction id
    Accepts:
        transaction: CTransaction
    Returns:
        transaction id (hex)
    """
    serialized = transaction.serialize()
    h = Hash(serialized)
    return b2lx(h)


def validate_bitcoin_address(address, network):
    """
    Validate address
    Accepts:
        address: string
        network: mainnet, testnet or None
    Returns:
        error message or None
    """
    if network:
        # TODO: don't set global params
        bitcoin.SelectParams(network)
        try:
            address = CBitcoinAddress(address)
        except:
            return 'Invalid address for network {0}.'.format(network)
    else:
        try:
            address = CBase58Data(address)
        except:
            return 'Invalid bitcoin address.'


def get_tx_fee(n_inputs, n_outputs, fee_per_kb):
    """
    Calculate transaction fee
    Accepts:
        n_inputs: number of inputs
        n_outputs: number of outputs
        fee_per_kb: fee per kilobyte
    """
    tx_size = n_inputs * 148 + n_outputs * 34 + 10 + n_inputs
    fee = fee_per_kb * (tx_size // 1024 + 1)
    return fee


def serialize_outputs(outputs):
    """
    Accepts:
        outputs: list of COutPoint instances
    Returns:
        byte string
    """
    buffer = StringIO()
    for outpoint in outputs:
        outpoint.stream_serialize(buffer)
    return buffer.getvalue()


def deserialize_outputs(string):
    """
    Accepts:
        string: serialized outputs
    Returns:
        list of COutPoint instances
    """
    buffer = StringIO(string)
    outputs = []
    while buffer.tell() < len(string):
        outpoint = COutPoint.stream_deserialize(buffer)
        outputs.append(outpoint)
    return outputs


def split_amount(amount, max_size):
    """
    Split bitcoin amount
    Accepts:
        amount: total amount, Decimal
        max_size: split size, Decimal
    Returns:
        list
    """
    splitted = []
    while amount > 0:
        if amount >= max_size:
            chunk = max_size
        else:
            chunk = amount
        amount -= chunk
        splitted.append(chunk)
    return splitted

from decimal import Decimal
import hashlib
import urllib

import bitcoin
import bitcoin.rpc
from bitcoin.core import COIN, x, lx, b2x, b2lx, CTransaction
from bitcoin.core.serialize import Hash
from bitcoin.wallet import CBitcoinAddress

from django.conf import settings

import payment
from payment import exceptions


class BlockChain(object):

    def __init__(self, network):
        self.network = network
        bitcoin.SelectParams(self.network)
        user, password = settings.BITCOIND_AUTH[network]
        service_url = "https://{user}:{password}@{host}:{port}".format(
            user=user,
            password=password,
            host=settings.BITCOIND_HOST,
            port=bitcoin.params.RPC_PORT)
        self._proxy = bitcoin.rpc.Proxy(service_url)

    def get_new_address(self):
        """
        Returns:
            address: CBitcoinAddress
        """
        address = self._proxy.getnewaddress()
        return address

    def get_address_balance(self, address):
        """
        Accepts:
            address: CBitcoinAddress
        Returns:
            balance: Decimal
        """
        minconf = 0
        balance = self._proxy.getreceivedbyaddress(str(address), minconf)
        return Decimal(balance).quantize(payment.BTC_DEC_PLACES)

    def get_unspent_outputs(self, address):
        """
        Accepts:
            address: CBitcoinAddress
        Returns:
            txouts: list of dicts
        """
        txouts = self._proxy.listunspent(minconf=0, addrs=[address])
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
        transaction_hex = self._proxy.createrawtransaction(
            inputs_, outputs_)
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
        network: mainnet or testnet
    Returns:
        error: error message
    """
    try:
        address = CBitcoinAddress(address)
    except:
        return "Invalid bitcoin address."
    if network is None:
        return None
    elif network == "mainnet":
        prefixes = bitcoin.MainParams.BASE58_PREFIXES.values()
    elif network == "testnet":
        prefixes = bitcoin.TestNetParams.BASE58_PREFIXES.values()
    if address.nVersion not in prefixes:
        return "Invalid address for network {0}.".format(network)


def get_tx_fee(inputs, outputs):
    """
    Calculate transaction fee
    Accepts:
        inputs: number of inputs,
        outputs: number of outputs
    """
    tx_size = inputs * 148 + outputs * 34 + 10 + inputs
    fee = payment.BTC_DEFAULT_FEE * (tx_size // 1024 + 1)
    return fee

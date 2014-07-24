from decimal import Decimal
import hashlib
import urllib

import bitcoin
import bitcoin.rpc
from bitcoin.core import COIN, x, b2x, b2lx, CTransaction
from bitcoin.core.serialize import Hash
from bitcoin.wallet import CBitcoinAddress

from django.conf import settings

import payment


class NetworkError(Exception):
    pass


class InvalidTransaction(Exception):
    pass


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
            txid = b2x(out['outpoint'].hash)
            transactions.append(self.get_raw_transaction(txid))
        return transactions

    def get_raw_transaction(self, transaction_id):
        """
        Accepts:
            transaction_id: hex string
        Returns:
            transaction: CTransaction
        """
        transaction = self._proxy.getrawtransaction(x(transaction_id))
        return transaction

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
        for address in outputs:
            amount = float(outputs[address])
            if amount > 0:
                outputs_[address] = amount
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
            raise InvalidTransaction
        return result['tx']

    def send_raw_transaction(self, transaction):
        """
        Accepts:
            transaction: CTransaction
        Returns:
            transaction_id: hex string
        """
        transaction_id = self._proxy.sendrawtransaction(transaction)
        return b2x(transaction_id)


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
        urllib.quote("Payment to {0}".format(name))
    )
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
    h = Hash(transaction.serialize())
    return b2x(h)


def get_tx_outputs(transaction):
    """
    Return transaction outputs
    Accepts:
        transaction: CTransaction
    Returns:
        outputs: list of outputs
    """
    outputs = []
    for output in transaction.vout:
        amount = Decimal(output.nValue) / COIN
        address = CBitcoinAddress.from_scriptPubKey(output.scriptPubKey)
        outputs.append({'amount': amount, 'address': address})
    return outputs

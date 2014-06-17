import binascii
from decimal import Decimal
import hashlib

import bitcoin
import bitcoin.rpc
from bitcoin.core import COIN, b2lx, CTransaction
from bitcoin.core.serialize import Hash

from django.conf import settings

import payment


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

    def is_valid_transaction(self, transaction):
        """
        Accepts:
            tx: CTransaction
        Returns:
            boolean
        """
        result = self._proxy.signrawtransaction(transaction)
        if result.get('complete') == 1:
            return True
        else:
            return False

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
                'txid': b2lx(outpoint.hash),
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
        transaction = CTransaction.deserialize(
            binascii.unhexlify(transaction_hex))
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
            transaction_id: string
        """
        transaction_id = self._proxy.sendrawtransaction(transaction)
        return b2lx(transaction_id)


class InvalidTransaction(Exception):
    pass


def construct_bitcoin_uri(address, amount_btc, request_url):
    """
    https://github.com/bitcoin/bips/blob/master/bip-0021.mediawiki
    Accepts:
        address: CBitcoinAddress
        amount_btc: Decimal
        request_url: url, string
    Returns:
        bitcoin uri: string
    """
    amount_btc = amount_btc.quantize(Decimal('0.00000000'))
    uri = "bitcoin:{address}?amount={amount}&r={request_url}".format(
        address=str(address),
        amount=str(amount_btc),
        request_url=request_url)
    return uri


def get_txid(transaction):
    """
    Calculate transaction id
    Accepts:
        transaction: CTransaction
    """
    h = Hash(transaction.serialize())
    return binascii.hexlify(h)

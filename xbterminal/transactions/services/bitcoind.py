from decimal import Decimal

from bitcoin.rpc import RawProxy, InvalidAddressOrKeyError

from django.conf import settings
from constance import config
from pycoin.serialize import b2h_rev
from pycoin.tx import Tx

from transactions.constants import COIN_DEC_PLACES, COIN_MIN_FEE
from transactions.exceptions import (
    DoubleSpend,
    TransactionModified)
from transactions.utils.compat import get_bitcoin_network
from transactions.utils.tx import from_units
from wallet.constants import COINS


class BlockChain(object):

    MAXCONF = 9999999

    def __init__(self, coin_name):
        self.pycoin_code = getattr(COINS, coin_name).pycoin_code
        if hasattr(settings, 'BITCOIND_SERVERS'):
            network = get_bitcoin_network(coin_name)
            config = settings.BITCOIND_SERVERS[network]
        else:
            config = settings.BLOCKCHAINS[coin_name]
        service_url = "http://{user}:{password}@{host}:{port}".format(
            user=config['USER'],
            password=config['PASSWORD'],
            host=config['HOST'],
            port=config['PORT'])
        self._proxy = RawProxy(service_url)

    def import_address(self, address, rescan=False):
        """
        Accepts:
            address: bitcoin address
            rescan: do blockchain rescan after import or not
        """
        label = ''
        result = self._proxy.importaddress(address, label, rescan)
        if result is not None:
            raise ValueError

    def get_address_balance(self, address):
        """
        Accepts:
            address: string
        Returns:
            balance: coin amount (Decimal)
        """
        minconf = 0
        txouts = self._proxy.listunspent(minconf, self.MAXCONF, [address])
        balance = sum(out['amount'] for out in txouts)
        return balance

    def get_raw_unspent_outputs(self, address, minconf=0):
        """
        Accepts:
            address: bitcoin address, string
        Returns:
            list of dicts
        """
        results = self._proxy.listunspent(
            minconf,
            self.MAXCONF,
            [address])
        return results

    def get_unspent_transactions(self, address):
        """
        Accepts:
            address: bitcoin address, string
        Returns:
            transactions: list of CTransaction
        """
        minconf = 0
        txouts = self._proxy.listunspent(minconf, self.MAXCONF, [address])
        transactions = []
        for out in txouts:
            transactions.append(self.get_raw_transaction(out['txid']))
        return transactions

    def get_raw_transaction(self, transaction_id):
        """
        Accepts:
            transaction_id: hex string
        Returns:
            transaction: pycoin Tx object
        """
        tx_hex = self._proxy.getrawtransaction(transaction_id)
        return Tx.from_hex(tx_hex)

    def get_tx_inputs(self, transaction):
        """
        Return transaction inputs
        Accepts:
            transaction: pycoin Tx object
        Returns:
            list of inputs (Decimal amount, address)
        """
        inputs = []
        for txin in transaction.txs_in:
            input_tx_id = b2h_rev(txin.previous_hash)
            input_tx_info = self._proxy.getrawtransaction(input_tx_id, 1)
            input_tx_out = input_tx_info['vout'][txin.previous_index]
            amount = Decimal(input_tx_out['value'])
            address = input_tx_out['scriptPubKey']['addresses'][0]
            inputs.append({'amount': amount, 'address': address})
        return inputs

    def get_tx_outputs(self, transaction):
        """
        Return transaction outputs
        Accepts:
            transaction: pycoin Tx object
        Returns:
            outputs: list of outputs
        """
        outputs = []
        for txout in transaction.txs_out:
            amount = from_units(txout.coin_value)
            address = txout.address(netcode=self.pycoin_code)
            outputs.append({'amount': amount, 'address': address})
        return outputs

    def is_tx_valid(self, transaction):
        """
        Accepts:
            transaction: pycoin Tx object
        Returns:
            True of False
        """
        tx_hex = transaction.as_hex()
        result = self._proxy.signrawtransaction(tx_hex)
        if result.get('complete') != 1:
            # Signing attempt for confirmed TX will return complete=False
            tx_id = transaction.id()
            if not self.is_tx_confirmed(tx_id, minconf=1):
                return False
        return True

    def send_raw_transaction(self, transaction):
        """
        Accepts:
            transaction: pycoin Tx object
        Returns:
            transaction_id: hex string
        """
        tx_hex = transaction.as_hex()
        transaction_id = self._proxy.sendrawtransaction(tx_hex)
        return transaction_id

    def is_tx_confirmed(self, tx_id, minconf=None):
        """
        Check for confirmation and get new transaction ID
        in case of malleability attack or double spend
        Accepts:
            tx_id: hex string
            minconf: number of required confirmations
        Returns:
            True or False
        """
        tx_info = self._proxy.gettransaction(tx_id)
        minconf = minconf or config.TX_REQUIRED_CONFIRMATIONS
        if tx_info['confirmations'] >= minconf:
            return True
        # Check conflicting transactions
        for conflicting_tx_id in tx_info['walletconflicts']:
            try:
                conflicting_tx_info = self._proxy.gettransaction(
                    conflicting_tx_id)
            except InvalidAddressOrKeyError:
                # Transaction already removed from mempool, skip
                continue
            if conflicting_tx_info['confirmations'] >= minconf:
                # Check for double spend
                if conflicting_tx_info['vout'] != tx_info['vout']:
                    raise DoubleSpend(conflicting_tx_id)
                raise TransactionModified(conflicting_tx_id)
        return False

    def get_tx_fee(self, n_inputs, n_outputs,
                   n_blocks=None):
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
        fee_per_kb = self._proxy.estimatefee(
            n_blocks or config.TX_EXPECTED_CONFIRM)
        if fee_per_kb == -1:
            fee_per_kb = config.TX_DEFAULT_FEE
        elif settings.DEBUG and fee_per_kb < config.TX_DEFAULT_FEE:
            # Always use TX_DEFAULT_FEE in stage and dev environments
            fee_per_kb = config.TX_DEFAULT_FEE
        elif fee_per_kb <= COIN_MIN_FEE:
            fee_per_kb = COIN_MIN_FEE
        return get_tx_fee(n_inputs, n_outputs, fee_per_kb)


def get_tx_fee(n_inputs, n_outputs, fee_per_kb):
    """
    Calculate transaction fee
    Accepts:
        n_inputs: number of inputs
        n_outputs: number of outputs
        fee_per_kb: fee per kilobyte
    """
    tx_size = n_inputs * 148 + n_outputs * 34 + 10 + n_inputs
    fee = (fee_per_kb / 1024) * tx_size
    return fee.quantize(COIN_DEC_PLACES)

import logging
from django.core.management.base import BaseCommand

from transactions.constants import BTC_DEC_PLACES
from transactions.models import (
    get_bitcoin_network,
    get_coin_type)
from transactions.deposits import prepare_deposit
from operations.blockchain import BlockChain
from website.models import Account


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Move funds from the old wallet to the new wallet'

    def add_arguments(self, parser):
        parser.add_argument('currency', type=str)

    def handle(self, *args, **options):
        for line in migrate_wallet(options['currency']):
            self.stdout.write(line)


def migrate_wallet(currency_name):
    coin_type = get_coin_type(currency_name)
    bitcoin_network = get_bitcoin_network(coin_type)
    bc = BlockChain(bitcoin_network)
    for account in Account.objects.filter(currency__name=currency_name):
        # Get unspent outputs
        tx_inputs = []
        tx_amount = BTC_DEC_PLACES
        for address in account.address_set.all():
            for output in bc.get_unspent_outputs(address.address):
                tx_inputs.append(output['outpoint'])
                tx_amount += output['amount']
        yield 'account: {}'.format(account)
        yield 'found {0} outputs, total amount {1}'.format(len(tx_inputs), tx_amount)
        tx_fee = bc.get_tx_fee(len(tx_inputs), 1)
        yield 'transaction fee {}'.format(tx_fee)
        # Create deposit
        deposit = prepare_deposit(account, 0)
        deposit.merchant_coin_amount = tx_amount - tx_fee
        assert deposit.fee_coin_amount == 0
        deposit.save()
        tx_outputs = {
            deposit.deposit_address.address: deposit.merchant_coin_amount,
        }
        transfer_tx = bc.create_raw_transaction(tx_inputs, tx_outputs)
        transfer_tx_signed = bc.sign_raw_transaction(transfer_tx)
        transfer_tx_id = bc.send_raw_transaction(transfer_tx_signed)
        yield 'transaction ID {}'.format(transfer_tx_id)
        yield '-----'

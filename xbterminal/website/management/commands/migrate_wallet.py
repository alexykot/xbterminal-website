import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from common.rq_helpers import run_periodic_task
from transactions.constants import BTC_DEC_PLACES, BTC_MIN_OUTPUT
from transactions.models import Deposit
from transactions.deposits import (
    wait_for_payment,
    check_deposit_status)
from transactions.utils.compat import get_bitcoin_network, get_coin_type
from operations.blockchain import BlockChain
from wallet.models import Address
from website.models import Account


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Move funds from the old wallet to the new wallet'

    def add_arguments(self, parser):
        parser.add_argument('currency', type=str)
        parser.add_argument('fee_address', type=str)
        parser.add_argument('--test', action='store_true')

    def handle(self, *args, **options):
        for line in migrate_wallet(options['currency'],
                                   options['fee_address'],
                                   options['test']):
            self.stdout.write(line)


@atomic
def migrate_wallet(currency_name, fee_address, is_test):
    coin_type = get_coin_type(currency_name)
    bitcoin_network = get_bitcoin_network(coin_type)
    bc = BlockChain(bitcoin_network)
    tx_inputs = []
    tx_outputs = {}
    tx_amount = BTC_DEC_PLACES
    deposits = []
    for account in Account.objects.filter(currency__name=currency_name):
        # Get unspent outputs
        account_amount = BTC_DEC_PLACES
        account_outputs = []
        for address in account.address_set.all():
            for output in bc.get_unspent_outputs(address.address):
                account_outputs.append(output['outpoint'])
                account_amount += output['amount']
        if not account_outputs:
            # No outputs
            continue
        yield 'merchant: {}'.format(account.merchant)
        yield 'found {0} outputs, total amount {1}'.format(
            len(account_outputs), account_amount)
        tx_inputs += account_outputs
        tx_amount += account_amount
        if is_test:
            tx_outputs[account.pk] = account_amount
            continue
        # Create deposit
        deposit_address = Address.create(coin_type, is_change=False)
        bc.import_address(deposit_address.address, rescan=False)
        tx_outputs[deposit_address.address] = account_amount
        deposit = Deposit.objects.create(
            account=account,
            currency=account.merchant.currency,
            amount=0,
            coin_type=coin_type,
            deposit_address=deposit_address,
            merchant_coin_amount=account_amount,
            fee_coin_amount=BTC_DEC_PLACES)
        deposits.append(deposit)
    # Create transaction
    yield '-----'
    fee_address_amount = BTC_DEC_PLACES
    for output in bc.get_unspent_outputs(fee_address):
        tx_inputs.append(output['outpoint'])
        fee_address_amount += output['amount']
    tx_fee = bc.get_tx_fee(len(tx_inputs), len(tx_outputs) + 1)
    yield 'transaction fee {}'.format(tx_fee)
    if is_test:
        return
    assert fee_address_amount - tx_fee > BTC_MIN_OUTPUT
    tx_outputs[fee_address] = fee_address_amount - tx_fee  # Change
    # Send transaction
    transfer_tx = bc.create_raw_transaction(tx_inputs, tx_outputs)
    transfer_tx_signed = bc.sign_raw_transaction(transfer_tx)
    transfer_tx_id = bc.send_raw_transaction(transfer_tx_signed)
    yield 'transaction ID: {}'.format(transfer_tx_id)
    # Start monitoring
    for deposit in deposits:
        run_periodic_task(wait_for_payment, [deposit.pk], interval=10)
        run_periodic_task(check_deposit_status, [deposit.pk], interval=60)

from django.core.management.base import BaseCommand

from website.models import Account
from operations import BTC_DEC_PLACES, blockchain


class Command(BaseCommand):

    help = 'Withdraws money from internal account to given address'

    def add_arguments(self, parser):
        parser.add_argument('account_id', type=int)
        parser.add_argument('address', type=str)

    def handle(self, *args, **options):
        result = withdraw_btc(options['account_id'], options['address'])
        self.stdout.write(result)


def withdraw_btc(account_id, address):
    try:
        account = Account.objects.get(pk=account_id)
    except Account.DoesNotExist:
        return 'invalid account id'
    if not account.address:
        return 'nothing to withdraw'
    if blockchain.validate_bitcoin_address(address, account.bitcoin_network):
        return 'invalid bitcoin address'
    bc = blockchain.BlockChain(account.bitcoin_network)
    tx_inputs = []
    amount = BTC_DEC_PLACES
    for output in bc.get_unspent_outputs(account.address):
        tx_inputs.append(output['outpoint'])
        amount += output['amount']
    if not amount:
        return 'nothing to withdraw'
    account.balance -= amount
    if account.balance != 0:
        return 'invalid balance'
    amount -= blockchain.get_tx_fee(len(tx_inputs), 1)
    tx_outputs = {address: amount}
    tx = bc.create_raw_transaction(tx_inputs, tx_outputs)
    tx_signed = bc.sign_raw_transaction(tx)
    tx_id = bc.send_raw_transaction(tx_signed)
    account.save()
    return ('sent {0} BTC to {1}, '
            'tx id {2}').format(amount, address, tx_id)

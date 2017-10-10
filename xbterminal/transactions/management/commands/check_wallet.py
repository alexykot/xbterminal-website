from decimal import Decimal
import logging
from django.core.management.base import BaseCommand

from transactions.services.bitcoind import BlockChain
from transactions.utils.compat import (
    get_coin_type,
    get_account_balance,
    get_fee_account_balance)
from wallet.models import Address
from website.models import Account

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Check database balances'

    def add_arguments(self, parser):
        parser.add_argument('currency', type=str)

    def handle(self, *args, **options):
        for line in check_wallet(options['currency']):
            self.stdout.write(line)


def check_wallet(currency_name):
    bc = BlockChain(currency_name)
    wallet_value = Decimal(0)
    db_value = Decimal(0)
    pool_size = 0
    for account in Account.objects.filter(currency__name=currency_name):
        db_value += get_account_balance(account, include_offchain=False)
    coin_type = get_coin_type(currency_name)
    db_value += get_fee_account_balance(coin_type, include_offchain=False)
    for address in Address.objects.filter(
            wallet_account__parent_key__coin_type=coin_type):
        address_balance = bc.get_address_balance(address.address)
        if address_balance > 0:
            wallet_value += address_balance
            pool_size += 1
    if wallet_value != db_value:
        logger.critical(
            'balance mismatch on %s wallet (%s != %s)',
            currency_name, wallet_value, db_value)
        yield 'balance mismatch, {0} != {1}'.format(wallet_value, db_value)
    else:
        yield 'total balance {}'.format(wallet_value)
    yield 'address pool size {}'.format(pool_size)

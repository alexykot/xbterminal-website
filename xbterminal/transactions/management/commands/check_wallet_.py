from decimal import Decimal
import logging
from django.core.management.base import BaseCommand

from transactions.models import (
    get_bitcoin_network,
    get_coin_type,
    get_account_balance,
    get_fee_account_balance)
from wallet.models import Address
from website.models import Account
from operations.blockchain import BlockChain

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Check database balances'

    def add_arguments(self, parser):
        parser.add_argument('currency', type=str)

    def handle(self, *args, **options):
        check_wallet(options['currency'])


def check_wallet(currency_name):
    coin_type = get_coin_type(currency_name)
    bitcoin_network = get_bitcoin_network(coin_type)
    bc = BlockChain(bitcoin_network)
    wallet_value = Decimal(0)
    db_value = Decimal(0)
    for account in Account.objects.filter(currency__name=currency_name):
        db_value += get_account_balance(account, include_offchain=False)
    db_value += get_fee_account_balance(coin_type, include_offchain=False)
    for address in Address.objects.filter(
            wallet_account__parent_key__coin_type=coin_type):
        wallet_value += bc.get_address_balance(address.address)
    if wallet_value != db_value:
        logger.critical(
            'balance mismatch on %s wallet (%s != %s)',
            currency_name, wallet_value, db_value)
    else:
        logger.info(
            'balance OK on %s wallet (%s total)',
            currency_name, wallet_value)

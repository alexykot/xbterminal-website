from decimal import Decimal
import logging
from django.core.management.base import BaseCommand

from website.models import Currency, Account
from operations.blockchain import BlockChain

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Compare merchants' balances and bitcoind wallet balance"

    def add_arguments(self, parser):
        # TODO: accept currency name as first argument
        parser.add_argument(
            'network', type=str, nargs='?', default='mainnet')
        parser.add_argument(
            '--strict', action='store_true')

    def handle(self, *args, **options):
        if options['strict']:
            check_wallet_strict(options['network'])
        else:
            check_wallet(options['network'])


def check_wallet(network):
    bc = BlockChain(network)
    currency = Currency.objects.get(
        name='BTC' if network == 'mainnet' else 'TBTC')
    wallet_value = Decimal(0)
    db_value = Decimal(0)
    for account in Account.objects.filter(currency=currency):
        for address in account.address_set.all():
            wallet_value += bc.get_address_balance(address.address)
        db_value += account.balance
    if wallet_value != db_value:
        logger.critical(
            'Balance mismatch on %s wallet (%s != %s)',
            network, wallet_value, db_value)
    else:
        logger.info(
            'Balance OK on %s wallet (%s total)',
            network, wallet_value)


def check_wallet_strict(network):
    bc = BlockChain(network)
    currency = Currency.objects.get(
        name='BTC' if network == 'mainnet' else 'TBTC')
    wallet_value = bc.get_balance(minconf=0)
    db_value = Decimal(0)
    for account in Account.objects.filter(currency=currency):
        db_value += account.balance
    if wallet_value != db_value:
        logger.critical(
            'Balance mismatch on %s wallet (%s != %s)',
            network, wallet_value, db_value)
    else:
        logger.info(
            'Balance OK on %s wallet (%s total)',
            network, wallet_value)

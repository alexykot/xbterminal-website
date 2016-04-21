from decimal import Decimal
import logging
from django.core.management.base import BaseCommand
from django.db.models import Sum

from website.models import Currency, Account
from website.utils import send_balance_admin_notification
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
    accounts = Account.objects.filter(currency=currency)
    wallet_value = Decimal(0)
    for address in accounts.values_list('bitcoin_address', flat=True):
        wallet_value += bc.get_address_balance(address)
    result = accounts.aggregate(Sum('balance'))
    db_value = result['balance__sum'] or Decimal(0)
    if wallet_value != db_value:
        send_balance_admin_notification({
            'network': network,
            'wallet_value': wallet_value,
            'db_value': db_value,
        })
        logger.critical('Balance mismatch on {0} wallet ({1} != {2})'.format(
            network, wallet_value, db_value))
    else:
        logger.info('Balance OK on {0} wallet ({1} total)'.format(
            network, wallet_value))


def check_wallet_strict(network):
    bc = BlockChain(network)
    currency = Currency.objects.get(
        name='BTC' if network == 'mainnet' else 'TBTC')
    wallet_value = bc.get_balance(minconf=0)
    result = Account.objects.filter(currency=currency).\
        aggregate(Sum('balance'))
    db_value = result['balance__sum'] or Decimal(0)
    if wallet_value != db_value:
        send_balance_admin_notification({
            'network': network,
            'wallet_value': wallet_value,
            'db_value': db_value,
        })
        logger.critical('Balance mismatch on {0} wallet ({1} != {2})'.format(
            network, wallet_value, db_value))
    else:
        logger.info('Balance OK on {0} wallet ({1} total)'.format(
            network, wallet_value))

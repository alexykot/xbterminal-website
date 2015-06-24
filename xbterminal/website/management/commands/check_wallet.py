from decimal import Decimal
import logging
from django.core.management.base import BaseCommand
from django.db.models import Sum

from website.models import BTCAccount
from website.utils import send_balance_admin_notification
from operations.blockchain import BlockChain

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Compare merchants' balances and bitcoind wallet balance"

    def handle(self, *args, **options):
        check_wallet('mainnet')
        check_wallet('testnet')


def check_wallet(network):
    bc = BlockChain(network)
    accounts = BTCAccount.objects.filter(network=network)
    wallet_value = Decimal(0)
    for address in accounts.values_list('address', flat=True):
        wallet_value += bc.get_address_balance(address)
    result = accounts.aggregate(Sum('balance'))
    db_value = result['balance__sum'] or Decimal(0)
    if wallet_value != db_value:
        send_balance_admin_notification({
            'network': network,
            'wallet_value': wallet_value,
            'db_value': db_value,
        })
        logger.critical('Balance mismatch on {0} wallet'.format(network))
    else:
        logger.info('Balance OK on {0} wallet'.format(network))


def check_wallet_strict(network):
    bc = BlockChain(network)
    wallet_value = bc.get_balance(minconf=0)
    result = BTCAccount.objects.filter(network=network).\
        aggregate(Sum('balance'))
    db_value = result['balance__sum'] or Decimal(0)
    if wallet_value != db_value:
        send_balance_admin_notification({
            'network': network,
            'wallet_value': wallet_value,
            'db_value': db_value,
        })
        logger.critical('Balance mismatch on {0} wallet'.format(network))
    else:
        logger.info('Balance OK on {0} wallet'.format(network))

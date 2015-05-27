import logging
from django.core.management.base import BaseCommand
from django.db.models import Sum

from website.models import BTCAccount
from website.utils import send_balance_admin_notification
from payment.blockchain import BlockChain

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Compare merchants' balances and bitcoind wallet balance"

    def handle(self, *args, **options):
        check_wallet('mainnet')
        check_wallet('testnet')


def check_wallet(network):
    bc = BlockChain(network)
    wallet_value = bc.get_balance(minconf=0)
    result = BTCAccount.objects.filter(network=network).\
        aggregate(Sum('balance'))
    db_value = result['balance__sum'] or 0
    if wallet_value != db_value:
        send_balance_admin_notification({
            'network': network,
            'wallet_value': wallet_value,
            'db_value': db_value,
        })
        logger.critical('Balance mismatch on {0} wallet'.format(network))
    else:
        logger.info('Balance OK on {0} wallet'.format(network))

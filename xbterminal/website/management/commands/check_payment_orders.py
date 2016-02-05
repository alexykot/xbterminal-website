import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from operations.blockchain import BlockChain
from operations.models import PaymentOrder

MESSAGE_TEMPLATE = ('merchant {merchant}, payment order {order_id}, '
                    'status {status}, address {address}, balance {balance}')


class Command(BaseCommand):

    help = 'Reports about failed payments'

    def add_arguments(self, parser):
        parser.add_argument('network', type=str)

    def handle(self, *args, **options):
        for line in check_payment_orders(options['network']):
            self.stdout.write(line)


def check_payment_orders(network):
    """
    Check local_address balance for all payment orders
    where transaction is not forwarded
    """
    bc = BlockChain(network)
    orders = PaymentOrder.objects.filter(
        bitcoin_network=network,
        time_created__lt=timezone.now() - datetime.timedelta(hours=6))
    for order in orders:
        balance = bc.get_address_balance(order.local_address)
        if balance > 0:
            yield MESSAGE_TEMPLATE.format(
                merchant=str(order.device.merchant),
                order_id=order.pk,
                status=order.status,
                address=order.local_address,
                balance=balance)

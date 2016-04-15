from decimal import Decimal

from django.core.management.base import BaseCommand

from bitcoin.core import COIN
import requests
import unicodecsv

from operations.models import PaymentOrder


class Command(BaseCommand):

    help = 'Analyzes transactions'

    def handle(self, *args, **options):
        with open('cpfp.csv', 'w') as csv_file:
            writer = unicodecsv.writer(csv_file, encoding='utf-8')
            for result in get_data():
                self.stdout.write(str(result))
                writer.writerow(result)


def get_data():
    for order in PaymentOrder.objects.filter(bitcoin_network='mainnet'):
        for tx_id in order.incoming_tx_ids:
            api_url = 'https://blockchain.info/rawtx/{0}/'.format(tx_id)
            response = requests.get(api_url)
            data = response.json()
            size = data['size']
            inp_sum = 0
            out_sum = 0
            for inp in data['inputs']:
                inp_sum += inp['prev_out']['value']
            for out in data['out']:
                out_sum += out['value']
            fee = Decimal(inp_sum - out_sum) / COIN
            yield tx_id, size, fee

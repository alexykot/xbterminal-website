import random

from django.core.management.base import BaseCommand

from wallet.constants import COINS, BIP44_PURPOSE
from wallet.models import WalletKey
from wallet.utils.keys import create_master_key, create_wallet_key


class Command(BaseCommand):

    help = 'Create new master key and save wallet keys to database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--secret',
            type=str,
            help='Secret string for master key generation.')

    def handle(self, *args, **options):
        secret = options['secret'] or str(random.getrandbits(100))
        master_key = create_master_key(secret)
        for coin in COINS:
            private_key = create_wallet_key(master_key,
                                            BIP44_PURPOSE,
                                            coin.pycoin_code,
                                            coin.bip44_type)
            wallet_key = WalletKey.objects.create(
                coin_type=coin.bip44_type,
                private_key=private_key)
            wallet_key.walletaccount_set.create()
        self.stdout.write(
            'Master private key: ' + master_key.hwif(as_private=True))
        self.stdout.write(
            'Master public key: ' + master_key.hwif(as_private=False))
        self.stdout.write('Derived keys are saved to database.')

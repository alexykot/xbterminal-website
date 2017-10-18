from django.core.management.base import BaseCommand

from wallet.constants import COINS, BIP44_PURPOSE
from wallet.models import WalletKey
from wallet.utils.keys import (
    deserialize_key,
    create_master_key,
    create_wallet_key,
    is_valid_master_key)


def get_input(message):
    return raw_input(message)


class Command(BaseCommand):

    help = 'Create new master key and save wallet keys to database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from-secret',
            action='store_true',
            help='Request secret string for master key generation.')

    def handle(self, *args, **options):
        if options['from_secret']:
            secret = get_input('Secret: ')
            master_key = create_master_key(secret)
            self.stdout.write(
                'Master private key: ' + master_key.hwif(as_private=True))
        else:
            master_key_wif = get_input('Master key: ')
            if not is_valid_master_key(master_key_wif):
                self.stdout.write(self.style.ERROR('Invalid master key.'))
                return
            master_key = deserialize_key(master_key_wif)
        for coin_name, coin in COINS.__members__.items():
            private_key = create_wallet_key(master_key,
                                            BIP44_PURPOSE,
                                            coin.pycoin_code,
                                            coin.bip44_type)
            wallet_key, created = WalletKey.objects.get_or_create(
                coin_type=coin.bip44_type,
                defaults={'private_key': private_key})
            if created:
                wallet_key.walletaccount_set.create()
                self.stdout.write(self.style.SUCCESS(
                    'Wallet key for coin {} saved to database.'.format(coin_name)))
            else:
                if wallet_key.private_key != private_key:
                    self.stdout.write(self.style.ERROR(
                        'Invalid master key.'))
                    return
                self.stdout.write(
                    'Wallet key for coin {} already exists.'.format(coin_name))

from django.core.management.base import BaseCommand

from website.models import MerchantAccount, INSTANTFIAT_PROVIDERS
from website.utils.accounts import (
    update_managed_accounts,
    update_balances)


class Command(BaseCommand):

    help = 'Imports accounts and transactions from CryptoPay'

    def handle(self, *args, **options):
        cryptopay_sync()


def cryptopay_sync():
    merchants = MerchantAccount.objects.filter(
        instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY)
    for merchant in merchants:
        update_managed_accounts(merchant)
        update_balances(merchant)

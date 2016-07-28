import logging

from django.core.management.base import BaseCommand

from operations.exceptions import CryptoPayInvalidAPIKey
from website.models import MerchantAccount, INSTANTFIAT_PROVIDERS
from website.utils.accounts import (
    update_managed_accounts,
    update_balances)
from website.utils.kyc import check_documents

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Imports accounts and transactions from CryptoPay'

    def handle(self, *args, **options):
        for line in cryptopay_sync():
            self.stdout.write(line)


def cryptopay_sync():
    merchants = MerchantAccount.objects.filter(
        instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
        instantfiat_api_key__isnull=False)
    for merchant in merchants:
        try:
            update_managed_accounts(merchant)
            update_balances(merchant)
            if merchant.has_managed_cryptopay_profile and \
                    merchant.verification_status == 'pending':
                check_documents(merchant)
        except CryptoPayInvalidAPIKey as error:
            # Remove invalid API key
            merchant.instantfiat_api_key = None
            merchant.save()
            logger.exception(error)
            yield '{0} - INVALID API KEY'.format(merchant.company_name)
        except Exception as error:
            logger.exception(error)
            yield '{0} - ERROR'.format(merchant.company_name)
        else:
            yield '{0} - SUCCESS'.format(merchant.company_name)

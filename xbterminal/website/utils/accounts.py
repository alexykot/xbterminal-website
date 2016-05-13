from operations.instantfiat.cryptopay import DEFAULT_CURRENCIES
from website.models import INSTANTFIAT_PROVIDERS


def check_managed_accounts(merchant):
    """
    Accepts:
        merchant: MerchantAccount instance
    Returns:
        True if all default CryptoPay accounts exist
            (and were created during registration)
        False otherwise
    """
    managed_accounts = merchant.account_set.filter(
        currency__name__in=DEFAULT_CURRENCIES,
        instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
        instantfiat_merchant_id__isnull=False)
    return managed_accounts.count() == len(DEFAULT_CURRENCIES)

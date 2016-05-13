from operations.instantfiat import cryptopay
from website.models import Currency, INSTANTFIAT_PROVIDERS


# TODO: remove function
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
        currency__name__in=cryptopay.DEFAULT_CURRENCIES,
        instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
        instantfiat_merchant_id__isnull=False)
    return managed_accounts.count() == len(cryptopay.DEFAULT_CURRENCIES)


def update_managed_accounts(merchant):
    """
    Create missing CryptoPay accounts, set account IDs
    Accepts:
        merchant: MerchantAccount instance
    """
    assert merchant.instantfiat_provider == INSTANTFIAT_PROVIDERS.CRYPTOPAY
    results = cryptopay.list_accounts(merchant.instantfiat_api_key)
    for item in results:
        currency = Currency.objects.get(name=item['currency'])
        account, created = merchant.account_set.get_or_create(
            currency=currency, instantfiat=True)
        account.instantfiat_account_id = item['id']
        account.save()

from operations.instantfiat import cryptopay
from website.models import Currency, INSTANTFIAT_PROVIDERS


def create_managed_accounts(merchant):
    """
    Create CryptoPay accounts
    Accepts:
        merchant: MerchantAccount instance
    """
    assert merchant.instantfiat_provider == INSTANTFIAT_PROVIDERS.CRYPTOPAY
    results = cryptopay.list_accounts(merchant.instantfiat_api_key)
    for item in results:
        merchant.account_set.create(
            currency=Currency.objects.get(name=item['currency']),
            instantfiat=True,
            instantfiat_account_id=item['id'])


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

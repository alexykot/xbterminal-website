from decimal import Decimal

from operations.instantfiat import cryptopay
from website.models import Currency, Transaction, INSTANTFIAT_PROVIDERS


def create_account_txs(order):
    """
    Create Transaction objects from order, update account balance
    Accepts:
        order: PaymentOrder or WithdrawalOrder instance
    """
    account = order.device.account
    if order.order_type == 'payment':
        if account.instantfiat:
            assert account.merchant.instantfiat_provider == INSTANTFIAT_PROVIDERS.CRYPTOPAY
            account.transaction_set.create(
                payment=order,
                amount=cryptopay.get_final_amount(order.instantfiat_fiat_amount))
        else:
            account.transaction_set.create(
                payment=order,
                amount=order.merchant_btc_amount)
    elif order.order_type == 'withdrawal':
        if account.instantfiat:
            account.transaction_set.create(
                withdrawal=order,
                amount=-order.fiat_amount)
        else:
            account.transaction_set.create(
                withdrawal=order,
                amount=-(order.btc_amount + order.change_btc_amount))
            if order.change_btc_amount > 0:
                account.transaction_set.create(
                    withdrawal=order,
                    amount=order.change_btc_amount)


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


def update_balances(merchant):
    """
    Import Transaction objects from CryptoPay
    Accepts:
        merchant: MerchantAccount instance
    """
    assert merchant.instantfiat_provider == INSTANTFIAT_PROVIDERS.CRYPTOPAY
    for account in merchant.account_set.filter(instantfiat=True):
        results = cryptopay.list_transactions(
            account.instantfiat_account_id,
            merchant.instantfiat_api_key)
        for item in results:
            amount_decimal = Decimal(format(item['amount'], '.15g'))
            try:
                transaction = account.transaction_set.get(
                    instantfiat_tx_id=item['id'])
            except Transaction.DoesNotExist:
                if item['type'] == 'Invoice':
                    # Try to find transaction by payment order
                    invoice_id = item['description'].split()[1].strip()
                    try:
                        transaction = account.transaction_set.get(
                            payment__instantfiat_invoice_id=invoice_id)
                    except Transaction.DoesNotExist:
                        # Create new transaction
                        transaction = account.transaction_set.create(
                            instantfiat_tx_id=item['id'],
                            amount=amount_decimal)
                    else:
                        # Transaction found, set ID
                        transaction.instantfiat_tx_id = item['id']
                        transaction.save()
                elif item['type'] == 'Bitcoin payment':
                    # Try to find transaction by withdrawal order
                    reference = item['reference']
                    try:
                        transaction = account.transaction_set.get(
                            withdrawal__instantfiat_reference=reference)
                    except Transaction.DoesNotExist:
                        # Create new transaction
                        transaction = account.transaction_set.create(
                            instantfiat_tx_id=item['id'],
                            amount=amount_decimal)
                    else:
                        # Transaction found, set ID
                        transaction.instantfiat_tx_id = item['id']
                        transaction.save()
                else:
                    # Create new transaction
                    transaction = account.transaction_set.create(
                        instantfiat_tx_id=item['id'],
                        amount=amount_decimal)
            # Check amount
            assert transaction.amount == amount_decimal

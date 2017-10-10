from django.apps import apps
from django.db.models import Sum, Q

from wallet.constants import COINS
from transactions.constants import COIN_DEC_PLACES


def get_bitcoin_network(coin_name):
    """
    For compatibility with python-bitcoinlib
    """
    if coin_name == 'BTC':
        network = 'mainnet'
    elif coin_name == 'TBTC':
        network = 'testnet'
    else:
        raise ValueError('Unsupported coin')
    return network


def get_coin_type(coin_name):
    """
    Determine coin type from currency name
    """
    coin = getattr(COINS, coin_name)
    return coin.bip44_type


def get_account_balance(account,
                        include_unconfirmed=True,
                        include_offchain=True):
    """
    Return total balance on account
    Accepts:
        account: Account instance
        include_unconfirmed: include unconfirmed changes, bool
        include_offchain: include reserved amounts
    """
    # TODO: replace old balance property
    if not include_unconfirmed:
        changes = account.balancechange_set.exclude_unconfirmed()
    else:
        changes = account.balancechange_set.all()
    if not include_offchain:
        changes = changes.exclude(withdrawal__isnull=False,
                                  withdrawal__time_sent__isnull=True)
    result = changes.aggregate(Sum('amount'))
    return result['amount__sum'] or COIN_DEC_PLACES


def get_fee_account_balance(coin_type,
                            include_unconfirmed=True,
                            include_offchain=True):
    """
    Return total collected fees
    """
    BalanceChange = apps.get_model('transactions', 'BalanceChange')
    if not include_unconfirmed:
        changes = BalanceChange.objects.exclude_unconfirmed()
    else:
        changes = BalanceChange.objects.all()
    if not include_offchain:
        changes = changes.exclude(withdrawal__isnull=False,
                                  withdrawal__time_sent__isnull=True)
    result = changes.\
        filter(address__wallet_account__parent_key__coin_type=coin_type).\
        filter(account__isnull=True).\
        aggregate(Sum('amount'))
    return result['amount__sum'] or COIN_DEC_PLACES


def get_address_balance(address, include_unconfirmed=True):
    """
    Return total balance on address
    Accepts:
        account: Account instance
        only_confirmed: whether to exclude unconfirmed changes, bool
    """
    if not include_unconfirmed:
        changes = address.balancechange_set.exclude_unconfirmed()
    else:
        changes = address.balancechange_set.all()
    result = changes.aggregate(Sum('amount'))
    return result['amount__sum'] or COIN_DEC_PLACES


def get_account_transactions(account):
    return account.balancechange_set.all()


def get_device_transactions(device):
    BalanceChange = apps.get_model('transactions', 'BalanceChange')
    return BalanceChange.objects.\
        filter(account__isnull=False).\
        filter(
            Q(deposit__device=device) |
            Q(withdrawal__device=device)).\
        order_by('created_at')

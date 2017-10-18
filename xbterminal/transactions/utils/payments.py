import urllib

from pycoin.key.validate import is_address_valid

from transactions.constants import COIN_DEC_PLACES
from wallet.constants import COINS


def construct_payment_uri(coin_name, address, amount, merchant_name,
                          *request_urls):
    """
    https://github.com/bitcoin/bips/blob/master/bip-0021.mediawiki
    Accepts:
        coin_name: coin name (currency name)
        address: address
        amount: Decimal
        merchant_name: merchant name
        request_urls: urls, strings
    Returns:
        payment uri: string
    """
    coin = getattr(COINS, coin_name)
    uri = '{0}:{1}?amount={2}&label={3}&message={4}'.format(
        coin.uri_prefix,
        address,
        str(amount.quantize(COIN_DEC_PLACES)),
        urllib.quote(merchant_name),
        urllib.quote(merchant_name))
    for idx, request_url in enumerate(request_urls):
        param_name = 'r' if idx == 0 else 'r{0}'.format(idx)
        uri += '&{0}={1}'.format(param_name, request_url)
    return uri


def validate_address(address, coin_name):
    """
    Validate address
    Accepts:
        address: string
        coin_name: coin name or None
    Returns:
        error message or None
    """
    if coin_name is not None:
        pycoin_code = getattr(COINS, coin_name).pycoin_code
        if not is_address_valid(address,
                                allowable_netcodes=[pycoin_code]):
            return 'Invalid address for coin {0}.'.format(coin_name)
    else:
        if not is_address_valid(address):
            return 'Invalid address.'

import urllib

from transactions.constants import BTC_DEC_PLACES
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
        str(amount.quantize(BTC_DEC_PLACES)),
        urllib.quote(merchant_name),
        urllib.quote(merchant_name))
    for idx, request_url in enumerate(request_urls):
        param_name = 'r' if idx == 0 else 'r{0}'.format(idx)
        uri += '&{0}={1}'.format(param_name, request_url)
    return uri

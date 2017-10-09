import requests
from constance import config

BLOCKCYPHER_CHAINS = {
    'BTC': 'main',
    'TBTC': 'test3',
}

BLOCKCYPHER_CHAINS_LIVE = {
    'BTC': 'btc',
    'TBTC': 'btc-testnet',
}


def get_tx_confidence(tx_id, coin_name):
    """
    http://dev.blockcypher.com/#transaction-confidence-endpoint
    """
    api_url = 'https://api.blockcypher.com/v1/btc/{chain}/txs/{tx_id}'.format(
        chain=BLOCKCYPHER_CHAINS[coin_name],
        tx_id=tx_id)
    payload = {'includeConfidence': 'true'}
    if config.BLOCKCYPHER_API_TOKEN:
        payload['token'] = config.BLOCKCYPHER_API_TOKEN
    response = requests.get(api_url, params=payload)
    response.raise_for_status()
    data = response.json()
    if data['confirmations'] >= 1:
        return 1.0
    return data.get('confidence', 0)


def get_tx_url(tx_id, coin_name):
    url = 'https://live.blockcypher.com/{0}/tx/{1}/'.format(
        BLOCKCYPHER_CHAINS_LIVE[coin_name], tx_id)
    return url


def get_address_url(address, coin_name):
    url = 'https://live.blockcypher.com/{0}/address/{1}/'.format(
        BLOCKCYPHER_CHAINS_LIVE[coin_name], address)
    return url

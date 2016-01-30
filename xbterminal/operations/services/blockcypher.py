import requests
from constance import config

BLOCKCYPHER_CHAINS = {
    'mainnet': 'main',
    'testnet': 'test3',
}

BLOCKCYPHER_CHAINS_LIVE = {
    'mainnet': 'btc',
    'testnet': 'btc-testnet',
}


def is_tx_reliable(tx_id, network):
    """
    http://dev.blockcypher.com/#transaction-confidence-endpoint
    """
    api_url = 'https://api.blockcypher.com/v1/btc/{chain}/txs/{tx_id}'
    response = requests.get(api_url.format(
        chain=BLOCKCYPHER_CHAINS[network],
        tx_id=tx_id))
    response.raise_for_status()
    data = response.json()
    if data['confirmations'] >= 1:
        return True
    elif data['confidence'] >= config.TX_CONFIDENCE_THRESHOLD:
        return True
    else:
        return False


def get_tx_url(tx_id, network):
    url = 'https://live.blockcypher.com/{0}/tx/{1}/'.format(
        BLOCKCYPHER_CHAINS_LIVE[network], tx_id)
    return url


def get_address_url(address, network):
    url = 'https://live.blockcypher.com/{0}/address/{1}/'.format(
        BLOCKCYPHER_CHAINS_LIVE[network], address)
    return url

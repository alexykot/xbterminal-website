import requests

BLOCKR = {
    'mainnet': 'https://btc.blockr.io',
    'testnet': 'https://tbtc.blockr.io',
}


def is_tx_broadcasted(tx_id, network):
    """
    Check transaction
    """
    api_url = '{0}/api/v1/tx/info/{1}'.format(BLOCKR[network], tx_id)
    try:
        response = requests.get(api_url)
        data = response.json()
    except (requests.exceptions.RequestException, ValueError):
        return None
    if data['status'] == 'success':
        return True
    return False


def get_tx_url(tx_id, network):
    url = '{0}/tx/info/{1}'.format(BLOCKR[network], tx_id)
    return url


def get_address_url(address, network):
    url = '{0}/address/info/{1}'.format(BLOCKR[network], address)
    return url

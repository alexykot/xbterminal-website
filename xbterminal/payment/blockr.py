import requests

BLOCKR = {
    'mainnet': 'http://btc.blockr.io',
    'testnet': 'http://tbtc.blockr.io',
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

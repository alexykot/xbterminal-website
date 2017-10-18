import requests

SOCHAIN_NETWORKS = {
    'BTC': 'BTC',
    'TBTC': 'BTCTEST',
    'DASH': 'DASH',
}


def get_tx_confidence(tx_id, coin_name):
    """
    https://chain.so/api#get-network-confidence
    """
    api_url = 'https://chain.so/api/v2/get_confidence/{network}/{tx_id}'.format(
        network=SOCHAIN_NETWORKS[coin_name],
        tx_id=tx_id)
    response = requests.get(api_url)
    response.raise_for_status()
    data = response.json()
    if data['data']['confirmations'] >= 1:
        return 1.0
    return data['data']['confidence']

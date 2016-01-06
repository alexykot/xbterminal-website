import requests

BLOCKCYPHER_CHAINS = {
    'mainnet': 'main',
    'testnet': 'test3',
}
BLOCKCYPHER_CONFIDENCE_THRESHOLD = 0.95


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
    elif data['confidence'] >= BLOCKCYPHER_CONFIDENCE_THRESHOLD:
        return True
    else:
        return False

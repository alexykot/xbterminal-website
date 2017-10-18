DASHORG_DOMAINS = {
    'DASH': 'explorer.dash.org',
    'TDASH': 'test.explorer.dash.org',
}


def get_tx_url(tx_id, coin_name):
    url = 'https://{0}/tx/{1}'.format(
        DASHORG_DOMAINS[coin_name], tx_id)
    return url


def get_address_url(address, coin_name):
    url = 'https://{0}/address/{1}'.format(
        DASHORG_DOMAINS[coin_name], address)
    return url

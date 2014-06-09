from decimal import Decimal

import bitcoin
import bitcoin.rpc


class BlockChain(object):

    def __init__(self, user, password, host, network):
        bitcoin.SelectParams(network)
        service_url = "https://{user}:{password}@{host}:{port}".format(
            user=user,
            password=password,
            host=host,
            port=bitcoin.params.RPC_PORT)
        self.proxy = bitcoin.rpc.Proxy(service_url)

    def get_fresh_address(self):
        address = self.proxy.getnewaddress()
        return str(address)


def construct_bitcoin_uri(address, amount, request_url):
    amount = Decimal(amount).quantize(Decimal('0.00000000'))
    uri = "bitcoin:{address}?amount={amount}&r={request_url}".format(
        address=address,
        amount=str(amount),
        request_url=request_url)
    return uri

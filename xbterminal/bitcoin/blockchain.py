from decimal import Decimal

from bitcoinrpc.connection import BitcoinConnection


class BlockChain(object):

    def __init__(self, user, password, host, port, use_https=True):
        self.conn = BitcoinConnection(user=user,
                                      password=password,
                                      host=host,
                                      port=port,
                                      use_https=use_https)

    def get_fresh_address(self):
        address = self.conn.getnewaddress()
        return address


def construct_bitcoin_uri(address, amount, request_url):
    amount = Decimal(amount).quantize(Decimal('0.00000000'))
    uri = "bitcoin:{address}?amount={amount}&r={request_url}".format(
        address=address,
        amount=str(amount),
        request_url=request_url)
    return uri

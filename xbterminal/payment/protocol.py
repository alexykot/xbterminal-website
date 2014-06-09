"""
https://github.com/bitcoin/bips/blob/master/bip-0070.mediawiki
"""
from decimal import Decimal
import time

import bitcoin
from bitcoin.wallet import CBitcoinAddress

from paymentrequest_pb2 import Output, PaymentDetails, PaymentRequest


def create_output(amount_btc, address):
    output = Output()
    # Convert to satoshis
    output.amount = int(amount_btc / Decimal('0.00000001'))
    # Convert address to script
    output.script = CBitcoinAddress(address).to_scriptPubKey()
    return output


def create_payment_details(outputs, payment_url, memo):
    details = PaymentDetails()
    if bitcoin.params.NAME == "mainnet":
        details.network = "main"
    elif bitcoin.params.NAME == "testnet":
        details.network = "test"
    details.outputs.extend([create_output(am, ad) for am, ad in outputs])
    details.time = int(time.time())
    if memo is not None:
        details.memo =  memo
    details.payment_url = payment_url
    return details


def create_payment_request(outputs, payment_url, memo=None):
    """
    Accepts:
        outputs: list of (amount, address) pairs
        payment_url: location where a Payment message may be sent
        memo: note that should be displayed to the customer
    """
    request = PaymentRequest()
    details = create_payment_details(outputs, payment_url, memo)
    request.serialized_payment_details = details.SerializeToString()
    return request

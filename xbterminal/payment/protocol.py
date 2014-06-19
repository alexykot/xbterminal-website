"""
https://github.com/bitcoin/bips/blob/master/bip-0070.mediawiki
"""
from decimal import Decimal
import time

from bitcoin.core import CTransaction
from bitcoin.wallet import CBitcoinAddress

from payment import paymentrequest_pb2


def create_output(address, amount):
    """
    Accepts:
        address: string
        amount: amount in BTC, Decimal
    """
    output = paymentrequest_pb2.Output()
    # Convert to satoshis
    output.amount = int(amount / Decimal('0.00000001'))
    # Convert address to script
    output.script = CBitcoinAddress(address).to_scriptPubKey()
    return output


def create_payment_details(network, outputs, created, expires,
                           payment_url, memo):
    """
    Accepts:
        network: "mainnet" or "testnet"
        outputs: list of (address, amount) pairs
        created: datetime
        expires: datetime
        payment_url: location where a Payment message may be sent
        memo: note that should be displayed to the customer
    """
    details = paymentrequest_pb2.PaymentDetails()
    if network == "mainnet":
        details.network = "main"
    elif network == "testnet":
        details.network = "test"
    details.outputs.extend([create_output(ad, am) for ad, am in outputs])
    details.time = int(time.mktime(created.timetuple()))
    details.expires = int(time.mktime(expires.timetuple()))
    details.memo =  memo
    details.payment_url = payment_url
    return details


def create_payment_request(*args):
    request = paymentrequest_pb2.PaymentRequest()
    details = create_payment_details(*args)
    request.serialized_payment_details = details.SerializeToString()
    return request


def parse_payment(message):
    """
    Aceepts:
        message: pb2-encoded message
    Returns:
        transations: list of CTransaction
        payment_ack: PaymentACK message
    """
    payment = paymentrequest_pb2.Payment()
    payment.ParseFromString(message)
    transactions = []
    for tx in payment.transactions:
        transactions.append(CTransaction.deserialize(tx))
    payment_ack = create_payment_ack(payment)
    return transactions, payment_ack


def create_payment_ack(payment):
    payment_ack = paymentrequest_pb2.PaymentACK()
    payment_ack.payment.CopyFrom(payment)
    return payment_ack

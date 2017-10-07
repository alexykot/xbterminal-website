"""
https://github.com/bitcoin/bips/blob/master/bip-0070.mediawiki
"""
from decimal import Decimal
import logging
import time
import os

import bitcoin
from bitcoin.core import CTransaction, CScript
from bitcoin.wallet import CBitcoinAddress

from django.conf import settings

from transactions.utils import paymentrequest_pb2, x509
from transactions.utils.compat import get_bitcoin_network

logger = logging.getLogger(__name__)


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


def create_payment_details(coin_name, outputs, created, expires,
                           payment_url, memo):
    """
    Accepts:
        coin_name: coin name (currency name)
        outputs: list of (address, amount) pairs
        created: datetime
        expires: datetime
        payment_url: location where a Payment message may be sent
        memo: note that should be displayed to the customer
    """
    details = paymentrequest_pb2.PaymentDetails()
    network = get_bitcoin_network(coin_name)
    bitcoin.SelectParams(network)
    if network == "mainnet":
        details.network = "main"
    elif network == "testnet":
        details.network = "test"
    details.outputs.extend([create_output(ad, am) for ad, am in outputs])
    details.time = int(time.mktime(created.timetuple()))
    details.expires = int(time.mktime(expires.timetuple()))
    details.memo = memo
    details.payment_url = payment_url
    return details


def create_pki_data(certificates):
    """
    Accepts:
        certificates: list of DER-encoded certificates
    """
    pki_data = paymentrequest_pb2.X509Certificates()
    for cert in certificates:
        pki_data.certificate.append(cert)
    return pki_data.SerializeToString()


def create_payment_request(*args):
    """
    Accepts:
        args: arguments for create_payment_details function
    """
    request = paymentrequest_pb2.PaymentRequest()
    details = create_payment_details(*args)
    request.serialized_payment_details = details.SerializeToString()
    if settings.PKI_KEY_FILE:
        # Prepare certificates and private key
        certificates = []
        for file_name in settings.PKI_CERTIFICATES:
            der_data = x509.read_cert_file(
                os.path.join(settings.CERT_PATH, file_name))
            certificates.append(der_data)
        # Sign payment request
        request.pki_type = "x509+sha256"
        request.pki_data = create_pki_data(certificates)
        request.signature = ""
        signature = x509.create_signature(
            request.SerializeToString(),
            os.path.join(settings.CERT_PATH, settings.PKI_KEY_FILE))
        request.signature = signature
    return request.SerializeToString()


def parse_output(output):
    """
    Accepts:
        output: Output object
    Returns:
        address: string
    """
    script = CScript(output.script)
    address = CBitcoinAddress.from_scriptPubKey(script)
    return str(address)


def parse_payment(coin_name, message):
    """
    Aceepts:
        coin_name: coin name
        message: pb2-encoded message
    Returns:
        transations: list of CTransaction
        refund_addresses: list of strings
        payment_ack: PaymentACK message
    """
    payment = paymentrequest_pb2.Payment()
    payment.ParseFromString(message)
    network = get_bitcoin_network(coin_name)
    bitcoin.SelectParams(network)
    transactions = []
    for tx in payment.transactions:
        transactions.append(CTransaction.deserialize(tx))
    refund_addresses = []
    for output in payment.refund_to:
        refund_addresses.append(parse_output(output))
    payment_ack = create_payment_ack(payment)
    return transactions, refund_addresses, payment_ack


def create_payment_ack(payment):
    payment_ack = paymentrequest_pb2.PaymentACK()
    payment_ack.payment.CopyFrom(payment)
    payment_ack.memo = "ack"
    return payment_ack.SerializeToString()

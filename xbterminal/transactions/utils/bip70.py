"""
https://github.com/bitcoin/bips/blob/master/bip-0070.mediawiki
"""
from decimal import Decimal
import logging
import time
import os

import bitcoin
from bitcoin.core import CTransaction
from pycoin.tx.pay_to import script_obj_from_script
from pycoin.ui import standard_tx_out_script

from django.conf import settings

from transactions.utils import paymentrequest_pb2, x509
from transactions.utils.compat import get_bitcoin_network
from wallet.constants import COINS

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
    output.script = standard_tx_out_script(address)
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
    if coin_name == 'BTC':
        details.network = 'main'
    elif coin_name == 'TBTC':
        details.network = 'test'
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
    pycoin_code = getattr(COINS, coin_name).pycoin_code
    transactions = []
    for tx in payment.transactions:
        transactions.append(CTransaction.deserialize(tx))
    refund_addresses = []
    for output in payment.refund_to:
        refund_address = script_obj_from_script(output.script).\
            address(netcode=pycoin_code)
        refund_addresses.append(refund_address)
    payment_ack = create_payment_ack(payment)
    return transactions, refund_addresses, payment_ack


def create_payment_ack(payment):
    payment_ack = paymentrequest_pb2.PaymentACK()
    payment_ack.payment.CopyFrom(payment)
    payment_ack.memo = "ack"
    return payment_ack.SerializeToString()

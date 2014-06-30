import base64

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Util.asn1 import DerSequence


def read_pem_file(filename):
    """
    Read data from file, convert from PEM to DER
    Returns:
        DER data (bytes)
    """
    with open(filename) as f:
        pem = f.read()
        der = base64.b64decode(''.join(pem.splitlines()[1:-1]))
    return der


def get_public_key(der_data):
    """
    http://www.ietf.org/rfc/rfc3280.txt
    Accepts:
        der_data: DER-encoded certificate
    Returns:
        public_key: RSA key (instance)
    """
    cert = DerSequence()
    cert.decode(der_data)
    # Extract tbsCertificate field
    tbs_certificate = DerSequence()
    tbs_certificate.decode(cert[0])
    # Extract subjectPublicKeyInfo field
    subject_public_key_info = tbs_certificate[6]
    public_key = RSA.importKey(subject_public_key_info)
    return public_key


def get_private_key(der_data):
    """
    Accepts:
        der_data: DER-encoded key
    Returns:
        private_key: RSA key (instance)
    """
    private_key = RSA.importKey(der_data)
    return private_key


def create_signature(message, key):
    """
    Create PKCS#1 v1.5 signature using SHA256
    Accepts:
        message: text message
        key: RSA key (instance)
    Returns:
        signature
    """
    hsh = SHA256.new(message)
    signer = PKCS1_v1_5.new(key)
    signature = signer.sign(hsh)
    return signature

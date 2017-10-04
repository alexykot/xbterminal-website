from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding


def read_cert_file(filename):
    """
    Read data from file, convert from PEM to DER
    Returns:
        DER data (bytes)
    """
    with open(filename) as f:
        pem_data = f.read()
        cert = x509.load_pem_x509_certificate(pem_data, default_backend())
        der_data = cert.public_bytes(serialization.Encoding.DER)
    return der_data


def create_signature(message, key_path):
    """
    Accepts:
        message: text message
        key_path: path to private key (PEM)
    Returns:
        signature
    """
    with open(key_path) as f:
        pem_data = f.read()
    private_key = serialization.load_pem_private_key(
        pem_data,
        password=None,
        backend=default_backend())
    signer = private_key.signer(
        padding.PKCS1v15(),
        hashes.SHA256())
    signer.update(message)
    signature = signer.finalize()
    return signature

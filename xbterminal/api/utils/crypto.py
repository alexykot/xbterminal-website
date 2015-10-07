import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature


def load_public_key(public_key_pem):
    return serialization.load_pem_public_key(
        str(public_key_pem),
        backend=default_backend())


def verify_signature(public_key_pem, message, signature):
    """
    Accepts:
        public_key_pem: public key in PEM format
        message
        signature
    Returns:
        True if signature is valid, false otherwise
    """
    try:
        signature = base64.b64decode(signature)
    except TypeError:
        return False
    public_key = load_public_key(public_key_pem)
    verifier = public_key.verifier(
        signature,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())
    verifier.update(message)
    try:
        verifier.verify()
    except InvalidSignature:
        return False
    else:
        return True


def create_test_public_key():
    """
    Create secret key and public key, return public key
    (for testing purposes)
    """
    secret_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=512,
        backend=default_backend())
    public_key = secret_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    return public_key_pem.strip()


def create_test_signature(message):
    """
    Create secret key and sign message (for testing purposes)
    """
    secret_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=512,
        backend=default_backend())
    public_key = secret_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    signer = secret_key.signer(
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())
    signer.update(message)
    signature = signer.finalize()
    return public_key_pem, base64.b64encode(signature)

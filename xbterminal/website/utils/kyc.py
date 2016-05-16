from constance import config

from operations.instantfiat import cryptopay
from website.models import INSTANTFIAT_PROVIDERS, KYC_DOCUMENT_TYPES
from website.utils.email import send_verification_info

REQUIRED_DOCUMENTS = [
    KYC_DOCUMENT_TYPES.ID_FRONT,
    KYC_DOCUMENT_TYPES.ADDRESS,
]


def upload_documents(merchant, documents):
    """
    Upload unverified KYC documents to CryptoPay
    Accepts:
        merchant: MerchantAccount instance
        documents: list of KYCDocument instances
    """
    assert merchant.instantfiat_provider == INSTANTFIAT_PROVIDERS.CRYPTOPAY
    assert merchant.instantfiat_merchant_id
    assert merchant.verification_status == 'unverified'
    upload_id = cryptopay.upload_documents(
        merchant.instantfiat_merchant_id,
        [document.file for document in documents],
        config.CRYPTOPAY_API_KEY)
    for document in documents:
        document.instantfiat_document_id = upload_id
        document.status = 'unverified'
        document.save()
    merchant.verification_status = 'pending'
    merchant.save()
    send_verification_info(merchant, documents)

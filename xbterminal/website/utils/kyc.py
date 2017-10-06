from website.models import KYC_DOCUMENT_TYPES
from website.utils.email import send_verification_info

REQUIRED_DOCUMENTS = [
    KYC_DOCUMENT_TYPES.ID_FRONT,
    KYC_DOCUMENT_TYPES.ID_BACK,
    KYC_DOCUMENT_TYPES.ADDRESS,
]


def upload_documents(merchant, documents):
    """
    Upload unverified KYC documents to CryptoPay
    Accepts:
        merchant: MerchantAccount instance
        documents: list of KYCDocument instances
    """
    assert merchant.verification_status == 'unverified'
    for document in documents:
        document.status = 'unverified'
        document.save()
    merchant.verification_status = 'pending'
    merchant.save()
    send_verification_info(merchant, documents)

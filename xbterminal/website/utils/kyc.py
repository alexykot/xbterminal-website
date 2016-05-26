from constance import config

from operations.instantfiat import cryptopay
from website.models import INSTANTFIAT_PROVIDERS, KYC_DOCUMENT_TYPES
from website.utils.email import (
    send_verification_info,
    send_verification_notification)

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


def check_documents(merchant):
    assert merchant.instantfiat_provider == INSTANTFIAT_PROVIDERS.CRYPTOPAY
    assert merchant.instantfiat_merchant_id
    assert merchant.verification_status == 'pending'
    user_data = cryptopay.get_merchant(merchant.instantfiat_merchant_id,
                                       config.CRYPTOPAY_API_KEY)
    for kyc_info in user_data['kyc']:
        # Get current document set
        documents = merchant.kycdocument_set.filter(
            instantfiat_document_id=kyc_info['id'],
            status='unverified')
        if not documents:
            # Skip
            continue
        if kyc_info['status'] == 'in_review':
            continue
        elif kyc_info['status'] == 'declined':
            documents.update(status='denied')
            if not user_data['verified']:
                merchant.verification_status = 'unverified'
                merchant.save()
                send_verification_info(merchant, documents)
                send_verification_notification(merchant)
        elif kyc_info['status'] == 'accepted':
            documents.update(status='verified')
            if user_data['verified']:
                merchant.verification_status = 'verified'
                merchant.save()
                send_verification_info(merchant, documents)
                send_verification_notification(merchant)
        else:
            raise AssertionError

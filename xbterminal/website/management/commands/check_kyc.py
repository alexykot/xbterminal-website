import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from constance import config

from website.models import MerchantAccount
from website.utils import send_kyc_notification
from payment.instantfiat import gocoin

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        for merchant in MerchantAccount.objects.filter(verification_status='pending'):
            results = gocoin.check_kyc_documents(merchant, config.GOCOIN_API_KEY)
            documents = [
                merchant.get_kyc_document(1, 'unverified'),
                merchant.get_kyc_document(2, 'unverified'),
            ]
            # Parse results
            for document in documents:
                for result in results:
                    if result['id'] == document.gocoin_document_id:
                        document.status = result['status']
                        document.comment = result['denied_memo']
                        break
            if all(doc.status == 'verified' for doc in documents):
                # Both documents verified
                send_kyc_notification(merchant, 'verified')
                for doc in documents:
                    doc.save()
                merchant.verification_status = 'verified'
                merchant.save()
            elif any(doc.status == 'denied' for doc in documents):
                # One or both documents denied
                reason = ', '.join(doc.comment for doc in documents if doc.comment)
                send_kyc_notification(merchant, 'denied', reason=reason)
                for doc in documents:
                    doc.save()
                merchant.verification_status = 'unverified'
                merchant.save()

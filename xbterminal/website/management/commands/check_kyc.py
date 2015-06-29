import logging

from django.core.management.base import BaseCommand

from constance import config

from website.models import MerchantAccount
from website.utils import send_kyc_notification, send_kyc_admin_notification
from operations.instantfiat import gocoin

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Check uploaded KYC documents'

    def handle(self, *args, **options):
        for merchant in MerchantAccount.objects.filter(verification_status='pending'):
            results = gocoin.check_kyc_documents(merchant, config.GOCOIN_AUTH_TOKEN)
            # Get latest documents
            documents = [
                merchant.get_latest_kyc_document(1),
                merchant.get_latest_kyc_document(2),
            ]
            # Parse results, update documents
            statuses = set()
            for document in documents:
                assert document is not None
                for result in results:
                    if (
                        result['id'] == document.gocoin_document_id
                        and result['status'] in ['denied', 'verified']
                    ):
                        document.status = result['status']
                        document.comment = result['denied_memo']
                        document.save()
                        break
                statuses.add(document.status)
            if statuses == {'verified'}:
                # Both documents verified
                send_kyc_notification(merchant)
                send_kyc_admin_notification(merchant)
                merchant.verification_status = 'verified'
                merchant.save()
            elif statuses == {'denied'} or statuses == {'denied', 'verified'}:
                # One or both documents denied
                send_kyc_notification(merchant)
                send_kyc_admin_notification(merchant)
                merchant.verification_status = 'unverified'
                merchant.save()

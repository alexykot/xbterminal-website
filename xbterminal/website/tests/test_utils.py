from decimal import Decimal

from mock import patch, Mock
from django.conf import settings
from django.core import mail
from django.test import TestCase
from constance.test import override_config

from website.models import INSTANTFIAT_PROVIDERS, KYC_DOCUMENT_TYPES
from website.utils.accounts import (
    create_managed_accounts,
    update_managed_accounts,
    update_balances)
from website.utils.kyc import upload_documents, check_documents
from website.tests.factories import (
    MerchantAccountFactory,
    KYCDocumentFactory,
    AccountFactory,
    TransactionFactory)
from operations.tests.factories import (
    PaymentOrderFactory,
    WithdrawalOrderFactory)


class AccountsUtilsTestCase(TestCase):

    @patch('website.utils.accounts.cryptopay.list_accounts')
    def test_create_managed_accounts(self, list_mock):
        list_mock.return_value = [
            {'id': 'a1', 'currency': 'BTC'},
            {'id': 'a2', 'currency': 'GBP'},
            {'id': 'a3', 'currency': 'USD'},
            {'id': 'a4', 'currency': 'EUR'},
        ]
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_api_key='test-key')
        create_managed_accounts(merchant)
        self.assertEqual(merchant.account_set.count(), 4)
        account_btc = merchant.account_set.get(currency__name='BTC',
                                               instantfiat=True)
        self.assertEqual(account_btc.instantfiat_account_id, 'a1')
        account_eur = merchant.account_set.get(currency__name='EUR',
                                               instantfiat=True)
        self.assertEqual(account_eur.instantfiat_account_id, 'a4')

    @patch('website.utils.accounts.cryptopay.list_accounts')
    def test_update_managed_accounts(self, list_mock):
        list_mock.return_value = [
            {'id': 'a1', 'currency': 'BTC'},
            {'id': 'a2', 'currency': 'GBP'},
            {'id': 'a3', 'currency': 'USD'},
            {'id': 'a4', 'currency': 'EUR'},
        ]
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_api_key='test-key')
        AccountFactory.create(merchant=merchant,
                              currency__name='EUR',
                              instantfiat=True,
                              instantfiat_account_id='test')
        update_managed_accounts(merchant)
        self.assertEqual(merchant.account_set.count(), 4)
        account_btc = merchant.account_set.get(currency__name='BTC',
                                               instantfiat=True)
        self.assertEqual(account_btc.instantfiat_account_id, 'a1')
        account_eur = merchant.account_set.get(currency__name='EUR',
                                               instantfiat=True)
        self.assertEqual(account_eur.instantfiat_account_id, 'a4')

    @patch('website.utils.accounts.cryptopay.list_transactions')
    def test_update_balances(self, list_mock):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_api_key='test-key')
        account = AccountFactory.create(merchant=merchant,
                                        currency=merchant.currency,
                                        instantfiat=True,
                                        instantfiat_account_id='test-id')
        payment_tx = TransactionFactory.create(
            payment=PaymentOrderFactory.create(
                instantfiat_invoice_id='00bb555b-3ebc-4476-8aa8-214e28aa6c03'),
            account=account,
            amount=Decimal('0.55'))
        withdrawal_tx = TransactionFactory.create(
            withdrawal=WithdrawalOrderFactory.create(
                instantfiat_reference='BT95281015'),
            account=account,
            amount=Decimal('-0.35'))
        TransactionFactory.create(
            account=account,
            instantfiat_tx_id='115',
            amount=Decimal('1.15'))
        self.assertEqual(account.balance, Decimal('1.35'))
        list_mock.return_value = [
            {'id': 110, 'amount': 0.55, 'type': 'Invoice',
             'description': 'Order 00bb555b-3ebc-4476-8aa8-214e28aa6c03'},
            {'id': 112, 'amount': -0.35, 'type': 'Bitcoin payment',
             'reference': 'BT95281015'},
            {'id': 115, 'amount': 1.15, 'type': 'Card reload'},
            {'id': 117, 'amount': 0.65, 'type': 'Invoice',
             'description': 'Order 140a2e0d-07ce-4bdf-9ea3-91a774261355'},
            {'id': 120, 'amount': -0.85, 'type': 'Bitcoin payment',
             'reference': 'BT120200116'},
        ]
        update_balances(merchant)
        self.assertEqual(list_mock.call_args[0][0], 'test-id')
        self.assertEqual(list_mock.call_args[0][1], 'test-key')
        self.assertEqual(account.transaction_set.count(), 5)
        self.assertEqual(account.balance, Decimal('1.15'))
        payment_tx.refresh_from_db()
        self.assertEqual(payment_tx.instantfiat_tx_id, '110')
        withdrawal_tx.refresh_from_db()
        self.assertEqual(withdrawal_tx.instantfiat_tx_id, '112')


class KYCUtilsTestCase(TestCase):

    @override_config(CRYPTOPAY_API_KEY='testkey')
    @patch('operations.instantfiat.cryptopay.requests.post')
    def test_upload_documents(self, post_mock):
        post_mock.return_value = Mock(**{
            'json.return_value': {
                'status': 'in_review',
                'id': '36e2a91e-18d1-4e3c-9e82-8c63e01797be',
            },
        })
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='xxx')
        document_1 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_FRONT,
            status='uploaded')
        document_2 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_BACK,
            status='uploaded')
        document_3 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ADDRESS,
            status='uploaded')
        upload_documents(merchant, [document_1, document_2, document_3])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])
        merchant.refresh_from_db()
        self.assertEqual(merchant.verification_status, 'pending')
        document_1.refresh_from_db()
        document_2.refresh_from_db()
        document_3.refresh_from_db()
        self.assertEqual(document_1.status, 'unverified')
        self.assertEqual(document_1.instantfiat_document_id,
                         '36e2a91e-18d1-4e3c-9e82-8c63e01797be')
        self.assertEqual(document_2.status, 'unverified')
        self.assertEqual(document_2.instantfiat_document_id,
                         '36e2a91e-18d1-4e3c-9e82-8c63e01797be')
        self.assertEqual(document_3.status, 'unverified')
        self.assertEqual(document_3.instantfiat_document_id,
                         '36e2a91e-18d1-4e3c-9e82-8c63e01797be')

    @override_config(CRYPTOPAY_API_KEY='testkey')
    @patch('operations.instantfiat.cryptopay.requests.get')
    def test_check_documents_in_review(self, get_mock):
        upload_id = '22be57f5-e605-483e-8a01-d6708b020774'
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'verified': False,
                'kyc': [{
                    'status': 'in_review',
                    'id': upload_id,
                }],
            },
        })
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='xxx',
            verification_status='pending')
        document_1 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_FRONT,
            instantfiat_document_id=upload_id,
            status='unverified')
        document_2 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_BACK,
            instantfiat_document_id=upload_id,
            status='unverified')
        document_3 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ADDRESS,
            instantfiat_document_id=upload_id,
            status='unverified')
        check_documents(merchant)
        self.assertEqual(len(mail.outbox), 0)
        merchant.refresh_from_db()
        self.assertEqual(merchant.verification_status, 'pending')
        document_1.refresh_from_db()
        document_2.refresh_from_db()
        document_3.refresh_from_db()
        self.assertEqual(document_1.status, 'unverified')
        self.assertEqual(document_2.status, 'unverified')
        self.assertEqual(document_3.status, 'unverified')

    @override_config(CRYPTOPAY_API_KEY='testkey')
    @patch('operations.instantfiat.cryptopay.requests.get')
    def test_check_documents_declined(self, get_mock):
        upload_id = '22be57f5-e605-483e-8a01-d6708b020774'
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'verified': False,
                'kyc': [{
                    'status': 'declined',
                    'id': upload_id,
                }],
            },
        })
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='xxx',
            verification_status='pending')
        document_1 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_FRONT,
            instantfiat_document_id=upload_id,
            status='unverified')
        document_2 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_BACK,
            instantfiat_document_id=upload_id,
            status='unverified')
        document_3 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ADDRESS,
            instantfiat_document_id=upload_id,
            status='unverified')
        check_documents(merchant)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to,
                         settings.CONTACT_EMAIL_RECIPIENTS)
        self.assertEqual(mail.outbox[1].to[0], merchant.user.email)
        merchant.refresh_from_db()
        self.assertEqual(merchant.verification_status, 'unverified')
        document_1.refresh_from_db()
        document_2.refresh_from_db()
        document_3.refresh_from_db()
        self.assertEqual(document_1.status, 'denied')
        self.assertEqual(document_2.status, 'denied')
        self.assertEqual(document_3.status, 'denied')

    @override_config(CRYPTOPAY_API_KEY='testkey')
    @patch('operations.instantfiat.cryptopay.requests.get')
    def test_check_documents_accepted(self, get_mock):
        upload_id = '22be57f5-e605-483e-8a01-d6708b020774'
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'verified': True,
                'kyc': [{
                    'status': 'accepted',
                    'id': upload_id,
                }],
            },
        })
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='xxx',
            verification_status='pending')
        document_1 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_FRONT,
            instantfiat_document_id=upload_id,
            status='unverified')
        document_2 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ID_BACK,
            instantfiat_document_id=upload_id,
            status='unverified')
        document_3 = KYCDocumentFactory.create(
            merchant=merchant,
            document_type=KYC_DOCUMENT_TYPES.ADDRESS,
            instantfiat_document_id=upload_id,
            status='unverified')
        check_documents(merchant)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to,
                         settings.CONTACT_EMAIL_RECIPIENTS)
        self.assertEqual(mail.outbox[1].to[0], merchant.user.email)
        merchant.refresh_from_db()
        self.assertEqual(merchant.verification_status, 'verified')
        document_1.refresh_from_db()
        document_2.refresh_from_db()
        document_3.refresh_from_db()
        self.assertEqual(document_1.status, 'verified')
        self.assertEqual(document_2.status, 'verified')
        self.assertEqual(document_3.status, 'verified')

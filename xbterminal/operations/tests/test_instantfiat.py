from decimal import Decimal
import json
from django.test import TestCase
from mock import patch, Mock

from website.models import INSTANTFIAT_PROVIDERS
from website.tests.factories import AccountFactory
from operations import instantfiat
from operations.exceptions import (
    InstantFiatError,
    CryptoPayUserAlreadyExists)


class InstantFiatTestCase(TestCase):

    @patch('operations.instantfiat.cryptopay.create_invoice')
    def test_create_invoice(self, create_invoice_mock):
        account = AccountFactory.create(
            currency__name='GBP',
            merchant__instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            merchant__instantfiat_api_key='test')
        create_invoice_mock.return_value = ('invoice_id',
                                            Decimal(0.1), 'address')
        result = instantfiat.create_invoice(account, Decimal(1.0))
        self.assertTrue(create_invoice_mock.called)
        call_args = create_invoice_mock.call_args[0]
        self.assertEqual(call_args[1], 'GBP')
        self.assertEqual(call_args[2], 'test')
        self.assertIn(account.merchant.company_name, call_args[3])
        self.assertEqual(result[0], 'invoice_id')
        self.assertEqual(result[1], Decimal(0.1))
        self.assertEqual(result[2], 'address')

    @patch('operations.instantfiat.cryptopay.is_invoice_paid')
    def test_is_invoice_paid(self, is_paid_mock):
        account = AccountFactory.create(
            currency__name='GBP',
            merchant__instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            merchant__instantfiat_api_key='test')
        is_paid_mock.return_value = True
        result = instantfiat.is_invoice_paid(account, 'invoice_id')
        self.assertEqual(is_paid_mock.call_args[0][0], 'invoice_id')
        self.assertEqual(is_paid_mock.call_args[0][1], 'test')
        self.assertTrue(result)

    @patch('operations.instantfiat.cryptopay.send_transaction')
    def test_send_transaction(self, send_mock):
        account = AccountFactory.create(
            currency__name='GBP',
            merchant__instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            merchant__instantfiat_api_key='test')
        send_mock.return_value = ('test-id', 'test-ref', Decimal('0.1'))
        result = instantfiat.send_transaction(
            account, Decimal('0.1'), 'bitcoin-address')
        self.assertEqual(send_mock.call_args[0][0],
                         account.instantfiat_account_id)
        self.assertEqual(send_mock.call_args[0][1],
                         account.currency.name)
        self.assertEqual(send_mock.call_args[0][4],
                         account.merchant.instantfiat_api_key)
        self.assertEqual(result[0], 'test-id')
        self.assertEqual(result[1], 'test-ref')
        self.assertEqual(result[2], Decimal('0.1'))

    @patch('operations.instantfiat.cryptopay.is_transfer_completed')
    def test_is_transfer_completed(self, is_completed_mock):
        account = AccountFactory.create(
            currency__name='GBP',
            merchant__instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            merchant__instantfiat_api_key='test')
        is_completed_mock.return_value = True
        result = instantfiat.is_transfer_completed(account, 'transfer_id')
        self.assertEqual(is_completed_mock.call_args[0][0], 'transfer_id')
        self.assertEqual(is_completed_mock.call_args[0][1],
                         account.merchant.instantfiat_api_key)
        self.assertTrue(result)


class CryptoPayTestCase(TestCase):

    @patch('operations.instantfiat.cryptopay.requests.post')
    def test_create_invoice(self, post_mock):
        post_mock.return_value = Mock(**{
            'json.return_value': {
                'uuid': 'invoice_id',
                'btc_price': 0.25,
                'btc_address': 'address',
            },
        })
        result = instantfiat.cryptopay.create_invoice(
            Decimal('1.0'), 'GBP', 'test', 'description')
        self.assertEqual(result[0], 'invoice_id')
        self.assertEqual(result[1], Decimal('0.25000000'))
        self.assertEqual(result[2], 'address')

    @patch('operations.instantfiat.cryptopay.requests.post')
    def test_create_invoice_error(self, post_mock):
        post_mock.return_value = Mock(**{
            'raise_for_status.side_effect': ValueError,
            'text': 'test',
        })
        with self.assertRaises(InstantFiatError) as error:
            instantfiat.cryptopay.create_invoice(
                Decimal('1.0'), 'GBP', 'test', 'description')
            self.assertEqual(str(error), 'test')

    @patch('operations.instantfiat.cryptopay.requests.get')
    def test_is_invoice_paid(self, get_mock):
        # Paid
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'status': 'paid',
            },
        })
        result = instantfiat.cryptopay.is_invoice_paid(
            'invoice_id', 'test')
        self.assertTrue(result)
        # Unpaid
        get_mock.return_value = Mock(**{
            'json.return_value': {'status': 'pending'},
        })
        result = instantfiat.cryptopay.is_invoice_paid(
            'invoice_id', 'test')
        self.assertFalse(result)

    @patch('operations.instantfiat.cryptopay.requests.get')
    def test_is_invoice_paid_error(self, get_mock):
        get_mock.return_value = Mock(**{
            'raise_for_status.side_effect': ValueError,
            'text': 'test',
        })
        result = instantfiat.cryptopay.is_invoice_paid(
            'invoice_id', 'test')
        self.assertFalse(result)

    def test_get_final_amount(self):
        amount_1 = Decimal('0.33')
        self.assertEqual(instantfiat.cryptopay.get_final_amount(amount_1),
                         Decimal('0.33'))
        amount_2 = Decimal('1.00')
        self.assertEqual(instantfiat.cryptopay.get_final_amount(amount_2),
                         Decimal('0.99'))
        amount_3 = Decimal('2.50')
        self.assertEqual(instantfiat.cryptopay.get_final_amount(amount_3),
                         Decimal('2.47'))

    @patch('operations.instantfiat.cryptopay.requests.post')
    def test_create_merchant(self, post_mock):
        post_mock.return_value = Mock(**{
            'json.return_value': {
                'id': '4437b1ac-d1e7-4a26-92bb-933d930d50b8',
                'email': 'john@example.com',
                'apikey': 'abcd1234',
            },
            'status_code': 201,
        })
        first_name = 'John'
        last_name = 'Doe'
        email = 'john@example.com'
        api_key = 'test-api-key'
        merchant_id, merchant_api_key = instantfiat.cryptopay.create_merchant(
            first_name, last_name, email, api_key)
        self.assertEqual(merchant_id,
                         '4437b1ac-d1e7-4a26-92bb-933d930d50b8')
        self.assertEqual(merchant_api_key, 'abcd1234')
        self.assertEqual(post_mock.call_args[1]['headers']['X-Api-Key'],
                         'test-api-key')

    @patch('operations.instantfiat.cryptopay.requests.post')
    def test_create_merchant_already_exists(self, post_mock):
        post_mock.return_value = Mock(**{
            'json.return_value': {
                'email': ['has already been taken'],
            },
            'status_code': 422,
        })
        with self.assertRaises(CryptoPayUserAlreadyExists):
            instantfiat.cryptopay.create_merchant(
                'fname', 'lname', 'email', 'key')

    @patch('operations.instantfiat.cryptopay.requests.post')
    def test_create_merchant_error(self, post_mock):
        post_mock.return_value = Mock(**{
            'json.return_value': {},
            'status_code': 422,
        })
        with self.assertRaises(Exception):
            instantfiat.cryptopay.create_merchant(
                'fname', 'lname', 'email', 'key')

    @patch('operations.instantfiat.cryptopay.requests.get')
    def test_get_merchant(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'id': '4437b1ac-d1e7-4a26-92bb-933d930d50b8',
            },
        })
        user_id = '4437b1ac-d1e7-4a26-92bb-933d930d50b8'
        api_key = 'test-api-key'
        user_data = instantfiat.cryptopay.get_merchant(user_id, api_key)
        self.assertEqual(user_data['id'], user_id)
        self.assertEqual(get_mock.call_args[1]['headers']['X-Api-Key'],
                         'test-api-key')

    @patch('operations.instantfiat.cryptopay.requests.post')
    def test_set_password(self, post_mock):
        post_mock.return_value = Mock(**{
            'json.return_value': {
                'status': 'success',
            },
        })
        user_id = '4437b1ac-d1e7-4a26-92bb-933d930d50b8'
        password = 'new-password'
        api_key = 'test-api-key'
        instantfiat.cryptopay.set_password(
            user_id, password, api_key)
        self.assertEqual(post_mock.call_args[1]['headers']['X-Api-Key'],
                         'test-api-key')

    @patch('operations.instantfiat.cryptopay.requests.post')
    def test_set_password_error(self, post_mock):
        post_mock.return_value = Mock(**{
            'json.return_value': {
                'status': 'success',
            },
            'raise_for_status.side_effect': ValueError,
        })
        user_id = '4437b1ac-d1e7-4a26-92bb-933d930d50b8'
        password = 'new-password'
        api_key = 'test-api-key'
        with self.assertRaises(InstantFiatError):
            instantfiat.cryptopay.set_password(
                user_id, password, api_key)

    @patch('operations.instantfiat.cryptopay.requests.post')
    def test_upload_documents(self, post_mock):
        post_mock.return_value = Mock(**{
            'json.return_value': {
                'status': 'in_review',
                'id': '36e2a91e-18d1-4e3c-9e82-8c63e01797be',
            },
        })
        user_id = '4437b1ac-d1e7-4a26-92bb-933d930d50b8'
        documents = []
        for content in ['aaa', 'bbb', 'ccc']:
            document = Mock(**{'read.return_value': content})
            document.name = 'test.jpg'
            documents.append(document)
        api_key = 'test-api-key'
        upload_id = instantfiat.cryptopay.upload_documents(
            user_id, documents, api_key)
        self.assertEqual(upload_id, '36e2a91e-18d1-4e3c-9e82-8c63e01797be')
        data = json.loads(post_mock.call_args[1]['data'])
        self.assertEqual(data['id_document_frontside'],
                         'data:image/jpeg;base64,YWFh')
        self.assertEqual(data['id_document_backside'],
                         'data:image/jpeg;base64,YmJi')
        self.assertEqual(data['residence_document'],
                         'data:image/jpeg;base64,Y2Nj')
        self.assertEqual(post_mock.call_args[1]['headers']['X-Api-Key'],
                         'test-api-key')

    @patch('operations.instantfiat.cryptopay.requests.get')
    def test_list_accounts(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': [
                {'id': 1, 'currency': 'BTC'},
                {'id': 2, 'currency': 'GBP'},
            ],
        })
        api_key = 'test-api-key'
        results = instantfiat.cryptopay.list_accounts(api_key)
        self.assertEqual(get_mock.call_args[1]['headers']['X-Api-Key'],
                         'test-api-key')
        self.assertEqual(len(results), 2)

    @patch('operations.instantfiat.cryptopay.requests.get')
    def test_list_transactions(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': [
                {'id': 1991, 'amount': 0.33},
                {'id': 1994, 'amount': -0.25},
            ],
        })
        account_id = '6bc3f1b4-a690-463a-8240-d47bcccba2a2'
        api_key = 'test-api-key'
        results = instantfiat.cryptopay.list_transactions(
            account_id, api_key)
        self.assertEqual(get_mock.call_args[1]['headers']['X-Api-Key'],
                         'test-api-key')
        self.assertEqual(len(results), 2)

    @patch('operations.instantfiat.cryptopay.requests.post')
    def test_send_transaction(self, post_mock):
        post_mock.return_value = Mock(**{
            'json.return_value': {
                'id': '36e2a91e-18d1-4e3c-9e82-8c63e01797be',
                'cryptopay_reference': 'BT120200116',
                'amount': '0.01',
            },
        })
        account_id = '6bc3f1b4-a690-463a-8240-d47bcccba2a2'
        currency_name = 'USD'
        amount = Decimal('0.01')
        destination = '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'
        api_key = 'test-api-key'
        transfer_id, reference, btc_amount = instantfiat.cryptopay.send_transaction(
            account_id, currency_name, amount, destination, api_key)
        self.assertEqual(transfer_id, '36e2a91e-18d1-4e3c-9e82-8c63e01797be')
        self.assertEqual(reference, 'BT120200116')
        self.assertEqual(btc_amount, Decimal('0.01'))
        data = json.loads(post_mock.call_args[1]['data'])
        self.assertEqual(data['amount_currency'], 'USD')
        self.assertEqual(data['amount'], 0.01)
        self.assertEqual(data['address'], destination)
        self.assertEqual(data['account'], account_id)
        self.assertEqual(post_mock.call_args[1]['headers']['X-Api-Key'],
                         api_key)

    @patch('operations.instantfiat.cryptopay.requests.get')
    def test_get_transfer(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'id': '36e2a91e-18d1-4e3c-9e82-8c63e01797be',
                'cryptopay_reference': 'BT120200116',
                'amount': '0.01',
                'status': 'new',
            },
        })
        transfer_id = '36e2a91e-18d1-4e3c-9e82-8c63e01797be'
        api_key = 'test-api-key'
        result = instantfiat.cryptopay.get_transfer(transfer_id, api_key)
        self.assertEqual(get_mock.call_args[1]['headers']['X-Api-Key'],
                         api_key)
        self.assertEqual(result['status'], 'new')

    @patch('operations.instantfiat.cryptopay.requests.get')
    def test_is_transfer_completed(self, get_mock):
        get_mock.return_value = Mock(**{
            'json.return_value': {
                'id': '36e2a91e-18d1-4e3c-9e82-8c63e01797be',
                'cryptopay_reference': 'BT120200116',
                'status': 'completed',
            },
        })
        transfer_id = '36e2a91e-18d1-4e3c-9e82-8c63e01797be'
        api_key = 'test-api-key'
        self.assertTrue(instantfiat.cryptopay.is_transfer_completed(
            transfer_id, api_key))

    @patch('operations.instantfiat.cryptopay.requests.get')
    def test_is_transfer_completed_error(self, get_mock):
        get_mock.side_effect = ValueError
        transfer_id = '36e2a91e-18d1-4e3c-9e82-8c63e01797be'
        api_key = 'test-api-key'
        self.assertFalse(instantfiat.cryptopay.is_transfer_completed(
            transfer_id, api_key))

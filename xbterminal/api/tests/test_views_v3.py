from decimal import Decimal
from mock import patch, Mock

from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django.utils import timezone

from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_jwt.settings import api_settings

from operations.tests.factories import (
    PaymentOrderFactory,
    WithdrawalOrderFactory)
from website.models import MerchantAccount, INSTANTFIAT_PROVIDERS
from website.tests.factories import (
    MerchantAccountFactory,
    AccountFactory,
    TransactionFactory,
    DeviceFactory)


def get_auth_token(user):
    jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
    jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
    payload = jwt_payload_handler(user)
    return jwt_encode_handler(payload)


class GetTokenViewTestCase(APITestCase):

    def test_get_token(self):
        merchant = MerchantAccountFactory.create()
        url = reverse('api:v3:token')
        data = {
            'email': merchant.user.email,
            'password': 'password',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)


class MerchantViewSetTestCase(APITestCase):

    def _get_token(self, user):
        url = reverse('api:v3:token')
        response = self.client.post(url, data={
            'email': user.email,
            'password': 'password',
        })
        return response.data['token']

    @patch('website.forms.cryptopay.create_merchant')
    @patch('website.forms.create_managed_accounts')
    def test_create(self, create_acc_mock, cryptopay_mock):
        cryptopay_mock.return_value = ('merchant_id', 'zxwvyx')
        url = reverse('api:v3:merchant-list')
        data = {
            'company_name': 'TestMerchant',
            'country': 'GB',
            'contact_first_name': 'Test',
            'contact_last_name': 'Test',
            'contact_email': 'test-mr@example.net',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        merchant = MerchantAccount.objects.get(pk=response.data['id'])
        self.assertEqual(merchant.company_name, data['company_name'])
        self.assertEqual(merchant.user.email, data['contact_email'])
        self.assertEqual(merchant.instantfiat_provider,
                         INSTANTFIAT_PROVIDERS.CRYPTOPAY)
        self.assertEqual(merchant.verification_status, 'unverified')
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[0].to[0], data['contact_email'])
        self.assertEqual(mail.outbox[1].to[0],
                         settings.CONTACT_EMAIL_RECIPIENTS[0])

    def test_create_error(self):
        url = reverse('api:v3:merchant-list')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['company_name'][0],
                         'This field is required.')

    def test_retrieve(self):
        merchant = MerchantAccountFactory.create()
        url = reverse('api:v3:merchant-detail',
                      kwargs={'pk': merchant.pk})
        auth = 'JWT {}'.format(self._get_token(merchant.user))
        response = self.client.get(url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], merchant.pk)
        self.assertEqual(response.data['verification_status'],
                         'unverified')

    def test_retrieve_no_auth(self):
        merchant = MerchantAccountFactory.create()
        url = reverse('api:v3:merchant-detail',
                      kwargs={'pk': merchant.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_no_merchant(self):
        url = reverse('api:v3:merchant-detail',
                      kwargs={'pk': 128718})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_another_merchant(self):
        merchant_1 = MerchantAccountFactory.create()
        merchant_2 = MerchantAccountFactory.create()
        url = reverse('api:v3:merchant-detail',
                      kwargs={'pk': merchant_1.pk})
        auth = 'JWT {}'.format(self._get_token(merchant_2.user))
        response = self.client.get(url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('api.views_v3.kyc.upload_documents')
    def test_upload_kyc(self, upload_mock):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='xxx')
        url = reverse('api:v3:merchant-upload-kyc',
                      kwargs={'pk': merchant.pk})
        auth = 'JWT {}'.format(self._get_token(merchant.user))
        data = {
            'id_document_frontside': 'data:image/png;base64,dGVzdA==',
            'id_document_backside': 'data:image/png;base64,dGVzdA==',
            'residence_document': 'data:image/png;base64,dGVzdA==',
        }
        response = self.client.post(url, data=data, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], merchant.pk)
        self.assertEqual(upload_mock.call_args[0][0].pk, merchant.pk)
        self.assertEqual(len(upload_mock.call_args[0][1]), 3)

    def test_upload_kyc_errors(self):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='xxx')
        url = reverse('api:v3:merchant-upload-kyc',
                      kwargs={'pk': merchant.pk})
        auth = 'JWT {}'.format(self._get_token(merchant.user))
        response = self.client.post(url, data={}, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['id_document_frontside'][0],
                         'This field is required.')

    def test_upload_kyc_no_cryptopay_account(self):
        merchant = MerchantAccountFactory.create()
        url = reverse('api:v3:merchant-upload-kyc',
                      kwargs={'pk': merchant.pk})
        auth = 'JWT {}'.format(self._get_token(merchant.user))
        response = self.client.post(url, data={}, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_upload_kyc_pending_verification(self):
        merchant = MerchantAccountFactory.create(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id='xxx',
            verification_status='verification_pending')
        url = reverse('api:v3:merchant-upload-kyc',
                      kwargs={'pk': merchant.pk})
        auth = 'JWT {}'.format(self._get_token(merchant.user))
        response = self.client.post(url, data={}, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DeviceViewSetTestCase(APITestCase):

    def test_create(self):
        merchant = MerchantAccountFactory.create()
        AccountFactory.create(merchant=merchant,
                              currency__name='GBP')
        url = reverse('api:v3:device-list')
        auth = 'JWT {}'.format(get_auth_token(merchant.user))
        data = {
            'name': 'PoS 12',
            'currency_code': 'GBP',
        }
        response = self.client.post(url, data, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], data['name'])
        self.assertEqual(response.data['currency_code'], data['currency_code'])
        self.assertIn('key', response.data)

    def test_create_no_auth(self):
        url = reverse('api:v3:device-list')
        data = {
            'name': 'PoS 12',
            'currency_code': 'GBP',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_error(self):
        merchant = MerchantAccountFactory.create()
        url = reverse('api:v3:device-list')
        auth = 'JWT {}'.format(get_auth_token(merchant.user))
        data = {
            'name': 'PoS 12',
            'currency_code': 'GBP',
        }
        response = self.client.post(url, data, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['currency_code'][0],
                         'Account does not exist.')

    def test_retrieve(self):
        device = DeviceFactory.create()
        url = reverse('api:v3:device-detail', kwargs={'key': device.key})
        auth = 'JWT {}'.format(get_auth_token(device.merchant.user))
        response = self.client.get(url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['key'], device.key)

    def test_retrieve_suspended(self):
        device = DeviceFactory.create(status='suspended')
        url = reverse('api:v3:device-detail', kwargs={'key': device.key})
        auth = 'JWT {}'.format(get_auth_token(device.merchant.user))
        response = self.client.get(url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_no_auth(self):
        device = DeviceFactory.create()
        url = reverse('api:v3:device-detail', kwargs={'key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_transactions(self):
        device = DeviceFactory.create()
        TransactionFactory.create(
            payment=PaymentOrderFactory.create(device=device),
            account=device.account)
        TransactionFactory.create(
            withdrawal=WithdrawalOrderFactory.create(device=device),
            account=device.account)
        url = reverse('api:v3:device-list-transactions',
                      kwargs={'key': device.key})
        auth = 'JWT {}'.format(get_auth_token(device.merchant.user))
        response = self.client.get(url, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_transactions_no_auth(self):
        device = DeviceFactory.create()
        url = reverse('api:v3:device-list-transactions',
                      kwargs={'key': device.key})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PaymentViewSetTestCase(APITestCase):

    @patch('api.views_v2.operations.payment.prepare_payment')
    def test_payment_init(self, prepare_mock):
        device = DeviceFactory.create()
        url = reverse('api:v3:payment-list')
        auth = 'JWT {}'.format(get_auth_token(device.merchant.user))
        prepare_mock.return_value = order = PaymentOrderFactory.create(
            device=device,
            fiat_amount=Decimal('0.50'),
            merchant_btc_amount=Decimal('0.0499'),
            tx_fee_btc_amount=Decimal('0.0001'))
        data = {
            'device': device.key,
            'amount': '0.50',
        }
        response = self.client.post(url, data, HTTP_AUTHORIZATION=auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uid'], order.uid)

    def test_payment_init_no_auth(self):
        device = DeviceFactory.create()
        url = reverse('api:v3:payment-list')
        data = {
            'device': device.key,
            'amount': '0.50',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('api.utils.pdf.get_template')
    def test_receipt_no_auth(self, get_template_mock):
        get_template_mock.return_value = Mock(**{
            'render.return_value': 'test',
        })
        order = PaymentOrderFactory.create(time_notified=timezone.now())
        url = reverse('api:v3:payment-receipt',
                      kwargs={'uid': order.uid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

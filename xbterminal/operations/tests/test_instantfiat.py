from decimal import Decimal
from django.test import TestCase
from mock import patch, Mock

from website.tests.factories import MerchantAccountFactory
from operations import instantfiat
from operations.exceptions import InstantFiatError


class InstantFiatTestCase(TestCase):

    @patch('operations.instantfiat.cryptopay.create_invoice')
    def test_create_invoice(self, create_invoice_mock):
        merchant = MerchantAccountFactory.create(
            payment_processor='cryptopay',
            api_key='test')
        create_invoice_mock.return_value = ('invoice_id',
                                            Decimal(0.1), 'address')
        result = instantfiat.create_invoice(merchant, Decimal(1.0))
        self.assertTrue(create_invoice_mock.called)
        call_args = create_invoice_mock.call_args[0]
        self.assertEqual(call_args[1], 'GBP')
        self.assertEqual(call_args[2], 'test')
        self.assertIn(merchant.company_name, call_args[3])
        self.assertEqual(result[0], 'invoice_id')
        self.assertEqual(result[1], Decimal(0.1))
        self.assertEqual(result[2], 'address')

    @patch('operations.instantfiat.cryptopay.is_invoice_paid')
    def test_is_invoice_paid(self, is_paid_mock):
        merchant = MerchantAccountFactory.create(
            payment_processor='cryptopay',
            api_key='test')
        is_paid_mock.return_value = True
        result = instantfiat.is_invoice_paid(merchant, 'invoice_id')
        self.assertEqual(is_paid_mock.call_args[0][0], 'invoice_id')
        self.assertEqual(is_paid_mock.call_args[0][1], 'test')
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

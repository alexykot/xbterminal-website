import unicodecsv

from mock import patch, Mock
from django.conf import settings
from django.core import mail
from django.test import TestCase

from website.models import Device, KYC_DOCUMENT_TYPES
from website.utils.devices import get_device_info, MAIN_PACKAGES
from website.utils.kyc import upload_documents
from website.utils.files import encode_base64, decode_base64
from website.utils.reports import (
    get_report_csv,
    get_report_filename)
from website.tests.factories import (
    MerchantAccountFactory,
    KYCDocumentFactory,
    DeviceFactory)
from transactions.tests.factories import BalanceChangeFactory


class DeviceUtilsTestCase(TestCase):

    @patch('website.utils.devices.Salt')
    def test_get_device_info(self, salt_cls_mock):
        versions = {
            'xbterminal-rpc': '1.0.0',
            'xbterminal-gui': '1.0.0',
        }
        salt_cls_mock.return_value = salt_mock = Mock(**{
            'get_pkg_versions.return_value': versions,
        })
        device = DeviceFactory.create()

        get_device_info(device.key)
        self.assertIs(salt_mock.login.called, True)
        self.assertEqual(salt_mock.get_pkg_versions.call_args[0][0],
                         device.key)
        self.assertEqual(salt_mock.get_pkg_versions.call_args[0][1],
                         MAIN_PACKAGES)
        updated_device = Device.objects.get(pk=device.pk)
        self.assertEqual(updated_device.system_info,
                         {'packages': versions})


class KYCUtilsTestCase(TestCase):

    def test_upload_documents(self):
        merchant = MerchantAccountFactory.create()
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
        self.assertTrue(all(doc.status == 'unverified' for doc
                            in merchant.kycdocument_set.all()))


class FileUtilsTestCase(TestCase):

    def test_encode_base64(self):
        file = Mock(**{'read.return_value': 'test'})
        file.name = 'test.jpg'
        data = encode_base64(file)
        self.assertEqual(data, 'data:image/jpeg;base64,dGVzdA==')

    def test_encode_base64_unknown_type(self):
        file = Mock(**{'read.return_value': 'test'})
        file.name = 'test.cvg'
        with self.assertRaises(AssertionError):
            encode_base64(file)

    def test_decode_base64(self):
        data = 'data:image/jpeg;base64,dGVzdA=='
        file = decode_base64(data)
        self.assertEqual(file.read(), 'test')
        self.assertEqual(file.name, '6447567a64413d3d.jpe')

    def test_decode_base64_unknown_type(self):
        data = 'data:xxxx/yyy;base64,ZCBmaWxl'
        with self.assertRaises(AssertionError):
            decode_base64(data)


class ReportUtilsTestCase(TestCase):

    def test_get_report_csv(self):
        transactions = BalanceChangeFactory.create_batch(3)
        report = get_report_csv(transactions)
        report.seek(0)
        rows = list(unicodecsv.reader(report, encoding='utf-8'))
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0][0], 'ID')
        self.assertEqual(rows[1][0], str(transactions[0].pk))
        self.assertEqual(rows[1][3], str(transactions[0].amount))
        self.assertEqual(rows[4][3],
                         str(sum(t.amount for t in transactions)))

    def test_get_report_filename(self):
        device = DeviceFactory.create(merchant__company_name='TestCo')
        result = get_report_filename(device)
        self.assertEqual(result, 'XBTerminal_transactions_TestCo.csv')

from django.test import TestCase

from website.templatetags import website_tags
from website.tests.factories import DeviceFactory


class TemplateTagsTestCase(TestCase):

    def test_amount(self):
        self.assertEqual(website_tags.amount(0.125, 'BTC'),
                         '0.12500000')
        self.assertEqual(website_tags.amount(0.175, 'DASH'),
                         '0.17500000')
        self.assertEqual(website_tags.amount(15, 'mBTC'),
                         '15.00000')
        self.assertEqual(website_tags.amount(15.2, 'USD'),
                         '15.20')

    def test_admin_url(self):
        device = DeviceFactory.create()
        url = website_tags.admin_url(device)
        self.assertIn('/admin/website/device/', url)

    def test_email_static(self):
        url = website_tags.email_static('img/xbt_email_footer.png')
        self.assertTrue(url.startswith('http'))

    def test_btc_tx_url(self):
        tx_id = '1' * 64
        result = website_tags.btc_tx_url(tx_id, 'BTC')
        self.assertIn(tx_id, result)

    def test_btc_address_url(self):
        address = 'a' * 32
        result = website_tags.btc_address_url(address, 'BTC')
        self.assertIn(address, result)

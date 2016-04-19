from django.test import TestCase

from website.templatetags import website_tags
from website.tests.factories import DeviceFactory


class TemplateTagsTestCase(TestCase):

    def test_admin_url(self):
        device = DeviceFactory.create()
        url = website_tags.admin_url(device)
        self.assertIn('/admin/website/device/', url)

    def test_btc_tx_url(self):
        tx_id = '1' * 64
        result = website_tags.btc_tx_url(tx_id, 'mainnet')
        self.assertIn(tx_id, result)

    def test_btc_address_url(self):
        address = 'a' * 32
        result = website_tags.btc_address_url(address, 'mainnet')
        self.assertIn(address, result)

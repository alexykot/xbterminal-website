from django.test import TestCase

from website.templatetags import website_tags


class TemplateTagsTestCase(TestCase):

    def test_btc_tx_url(self):
        tx_id = '1' * 64
        result = website_tags.btc_tx_url(tx_id, 'mainnet')
        self.assertIn(tx_id, result)

    def test_btc_address_url(self):
        address = 'a' * 32
        result = website_tags.btc_address_url(address, 'mainnet')
        self.assertIn(address, result)

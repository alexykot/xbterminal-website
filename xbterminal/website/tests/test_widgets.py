from django.test import TestCase

from website.widgets import (
    BitcoinAddressWidget,
    BitcoinTransactionWidget)


class BitcoinAddressWidgetTestCase(TestCase):

    def test_render(self):
        widget = BitcoinAddressWidget(network='testnet')
        result = widget.render('name', 'test')
        self.assertEqual(
            result,
            '<a target="_blank"'
            ' href="https://live.blockcypher.com/btc-testnet/address/test/">'
            'test</a>')


class BitcoinTransactionWidgetTestCase(TestCase):

    def test_render(self):
        widget = BitcoinTransactionWidget(network='testnet')
        result = widget.render('name', 'test')
        self.assertEqual(
            result,
            '<a target="_blank"'
            ' href="https://live.blockcypher.com/btc-testnet/tx/test/">'
            'test</a>')

import binascii

from django.test import TestCase

import bitcoin
from bitcoin.core import b2lx

from transactions.utils.bip70 import (
    parse_payment)


class BIP70UtilsTestCase(TestCase):

    def test_parse_payment(self):
        bitcoin.SelectParams('testnet')
        payment_message = binascii.unhexlify(
            '12e101010000000177b925097140496565508aa20440761091bcbcaa'
            'c352882988563d94bbd6a90f010000006a47304402206533bd1d0eb3'
            '04fe248392c895847565b43584dbaa346dbdbeee1eff6563eef30220'
            '797f6da5362e7aca4dc70fb7357135edebce9af0f1a09d304791c734'
            'ba86c0df0121037159aae32f6debc9a85d518feb5e6eaaaacfe674f3'
            'bd173c0e95be19e9db1a30ffffffff020dee2b00000000001976a914'
            '019fe0f656eac07d996aa840eb59ac34cc75c63f88ac2c8500000000'
            '00001976a9141ed5557f4914da4362c7bb25be78ae9386b4e76d88ac'
            '000000001a1f08ac8a02121976a914063ce37eef0c8b22b6ee8b68fd'
            '22b1bbc0f9d4b088ac')
        expected_transaction_id = ('62cc0fa8c7c7cd4a63aad51e2e038a4a0'
                                   '58cde2ea3b290ca76004cd69deee03e')
        expected_refund_address = 'mg5wHpgha1Qvd1stQ9MDAAPr4LSwe1QbUs'
        expected_payment_ack = binascii.unhexlify(
            '0a850212e101010000000177b925097140496565508aa20440761091'
            'bcbcaac352882988563d94bbd6a90f010000006a47304402206533bd'
            '1d0eb304fe248392c895847565b43584dbaa346dbdbeee1eff6563ee'
            'f30220797f6da5362e7aca4dc70fb7357135edebce9af0f1a09d3047'
            '91c734ba86c0df0121037159aae32f6debc9a85d518feb5e6eaaaacf'
            'e674f3bd173c0e95be19e9db1a30ffffffff020dee2b000000000019'
            '76a914019fe0f656eac07d996aa840eb59ac34cc75c63f88ac2c8500'
            '00000000001976a9141ed5557f4914da4362c7bb25be78ae9386b4e7'
            '6d88ac000000001a1f08ac8a02121976a914063ce37eef0c8b22b6ee'
            '8b68fd22b1bbc0f9d4b088ac120361636b')
        transactions, refund_addresses, payment_ack = \
            parse_payment(payment_message)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(b2lx(transactions[0].GetHash()),
                         expected_transaction_id)
        self.assertEqual(len(refund_addresses), 1)
        self.assertEqual(refund_addresses[0], expected_refund_address)
        self.assertEqual(payment_ack, expected_payment_ack)

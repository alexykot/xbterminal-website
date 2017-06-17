from decimal import Decimal

from django.test import TestCase

from pycoin.key.BIP32Node import BIP32Node

from transactions.utils.tx import create_tx, convert_tx


class TxUtilsTestCase(TestCase):

    def test_create_tx(self):
        tx_inputs = [{
            'txid': '81ce5b064d49224c27ac8256e13b6964'
                    'b71e0be59ee516dc9ccf303c39712273',
            'vout': 1,
            'amount': Decimal('0.005'),
            'scriptPubKey': '76a914b9dbfb58fddf964f6ab'
                            '8146e949a370850bc629a88ac',
            'private_key': BIP32Node.from_hwif(
                'tprv8km9JkJsMthQbmJqG9YgA23C1shqTFQy'
                'GcJK9BTsWjxyRdRVG3kHCPgcNtFEZSW9RM6D'
                'et955ePiQLRW2FTPVzsAQRPfoe4XGPq9ACLA7iw'),
        }]
        tx_outputs = {'n2p8YJojY7zewwt4ngonYUPgkV1xy7qfjR': Decimal('0.004')}
        tx = create_tx(tx_inputs, tx_outputs)
        self.assertIsNone(tx.check())
        self.assertIs(tx.missing_unspents(), False)
        self.assertEqual(tx.bad_signature_count(), 0)
        self.assertEqual(len(tx.id()), 64)
        self.assertEqual(tx.fee(), 100000)

        tx_ = convert_tx(tx)
        self.assertTrue(tx_.vin)
        self.assertTrue(tx_.vout)

    def test_create_tx_bad_signature(self):
        tx_inputs = [{
            'txid': '81ce5b064d49224c27ac8256e13b6964'
                    'b71e0be59ee516dc9ccf303c39712273',
            'vout': 1,
            'amount': Decimal('0.005'),
            'scriptPubKey': '76a914b9dbfb58fddf964f6ab'
                            '8146e949a370850bc629a88ac',
            'private_key': BIP32Node.from_hwif(
                'tprv8oMYy2BFqU2vWV6U9h6yDxSLfYXUKrvC'
                'dGDnKP365utwPc7cfubKPWkjSdxCsWAFArQj'
                'JkV4Eg5yJWELnEarzUyYcY3rZKZTNqHRU6JNN9H'),
        }]
        tx_outputs = {'n2p8YJojY7zewwt4ngonYUPgkV1xy7qfjR': Decimal('0.004')}
        with self.assertRaises(ValueError):
            create_tx(tx_inputs, tx_outputs)

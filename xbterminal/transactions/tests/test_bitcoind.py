from decimal import Decimal
from django.test import TestCase, override_settings
from mock import patch, Mock

from constance.test import override_config

from transactions.exceptions import TransactionModified, DoubleSpend
from transactions.constants import BTC_MIN_FEE
from transactions.services.bitcoind import (
    BlockChain,
    validate_bitcoin_address,
    get_tx_fee)


class BlockChainTestCase(TestCase):

    @patch('transactions.services.bitcoind.RawProxy')
    def test_init(self, proxy_cls_mock):
        bc = BlockChain('BTC')
        self.assertTrue(proxy_cls_mock.called)
        service_url = proxy_cls_mock.call_args[0][0]
        self.assertTrue(service_url.startswith('http'))
        self.assertEqual(bc.pycoin_code, 'BTC')

    @patch('transactions.services.bitcoind.RawProxy')
    def test_import_address(self, proxy_cls_mock):
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'importaddress.return_value': None,
        })
        address = '1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6'
        bc = BlockChain('BTC')
        bc.import_address('1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6')
        self.assertEqual(proxy_mock.importaddress.call_count, 1)
        self.assertEqual(proxy_mock.importaddress.call_args[0][0], address)
        self.assertEqual(proxy_mock.importaddress.call_args[0][1], '')
        self.assertIs(proxy_mock.importaddress.call_args[0][2], False)

    @patch('transactions.services.bitcoind.RawProxy')
    def test_get_address_balance(self, proxy_cls_mock):
        proxy_cls_mock.return_value = Mock(**{
            'listunspent.return_value': [{'amount': Decimal('0.005')}],
        })
        bc = BlockChain('BTC')
        balance = bc.get_address_balance('test')
        self.assertEqual(balance, Decimal('0.005'))

    @patch('transactions.services.bitcoind.RawProxy')
    def test_get_raw_unspent_outputs(self, proxy_cls_mock):
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'listunspent.return_value': [{'txid': '1' * 64}],
        })
        bc = BlockChain('BTC')
        outputs = bc.get_raw_unspent_outputs('test', minconf=1)
        self.assertEqual(outputs[0]['txid'], '1' * 64)
        self.assertEqual(proxy_mock.listunspent.call_args[0][0], 1)
        self.assertEqual(proxy_mock.listunspent.call_args[0][1], 9999999)
        self.assertEqual(proxy_mock.listunspent.call_args[0][2], ['test'])

    @patch('transactions.services.bitcoind.RawProxy')
    @patch('transactions.services.bitcoind.Tx.from_hex')
    def test_get_unspent_transactions(self, get_tx_mock, proxy_cls_mock):
        address = '1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6'
        transaction_id = '1' * 64
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'listunspent.return_value': [{
                'amount': 500000, 'txid': transaction_id,
            }],
            'getrawtransaction.return_value': 'abcd',
        })
        get_tx_mock.return_value = tx = Mock()
        bc = BlockChain('BTC')
        transactions = bc.get_unspent_transactions(address)

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions, [tx])
        self.assertEqual(proxy_mock.listunspent.call_count, 1)
        self.assertEqual(proxy_mock.listunspent.call_args[0][0], 0)
        self.assertEqual(proxy_mock.listunspent.call_args[0][2], [address])
        self.assertEqual(
            proxy_mock.getrawtransaction.call_args[0][0],
            transaction_id)

    @patch('transactions.services.bitcoind.RawProxy')
    @patch('transactions.services.bitcoind.Tx.from_hex')
    def test_get_raw_transaction(self, get_tx_mock, proxy_cls_mock):
        tx_id = '1' * 64
        get_tx_mock.return_value = tx = Mock()
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'getrawtransaction.return_value': 'abcd',
        })
        bc = BlockChain('BTC')
        result = bc.get_raw_transaction(tx_id)

        self.assertEqual(result, tx)
        self.assertIs(proxy_mock.getrawtransaction.called, True)
        self.assertEqual(get_tx_mock.call_args[0][0], 'abcd')

    @patch('transactions.services.bitcoind.RawProxy')
    def test_get_tx_inputs(self, proxy_cls_mock):
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'getrawtransaction.return_value': {
                'vout': [{
                    'value': '0.0001',
                    'scriptPubKey': {
                        'addresses': ['1A6Ei5cRfDJ8jjhwxfzLJph8B9ZEthR9Z'],
                    },
                }],
            },
        })
        bc = BlockChain('BTC')
        tx = Mock(txs_in=[Mock(previous_hash='\x11' * 32)])
        result = bc.get_tx_inputs(tx)

        self.assertEqual(result, [{
            'amount': Decimal('0.0001'),
            'address': '1A6Ei5cRfDJ8jjhwxfzLJph8B9ZEthR9Z',
        }])
        self.assertIs(proxy_mock.getrawtransaction.called, True)
        self.assertEqual(proxy_mock.getrawtransaction.call_args[0][0],
                         '1' * 64)
        self.assertIs(proxy_mock.getrawtransaction.call_args[0][1], True)

    def test_get_tx_outputs(self):
        bc = BlockChain('BTC')
        tx = Mock(txs_out=[Mock(**{
            'coin_value': 10000,
            'address.return_value': '1A6Ei5cRfDJ8jjhwxfzLJph8B9ZEthR9Z',
        })])
        result = bc.get_tx_outputs(tx)

        self.assertEqual(result, [{
            'amount': Decimal('0.0001'),
            'address': '1A6Ei5cRfDJ8jjhwxfzLJph8B9ZEthR9Z',
        }])

    @patch('transactions.services.bitcoind.RawProxy')
    def test_is_tx_valid(self, proxy_cls_mock):
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'signrawtransaction.return_value': {
                'complete': True,
            },
        })
        tx = Mock(**{'as_hex.return_value': 'abcd'})
        bc = BlockChain('BTC')
        result = bc.is_tx_valid(tx)

        self.assertIs(result, True)
        self.assertEqual(proxy_mock.signrawtransaction.call_args[0][0],
                         'abcd')

    @patch('transactions.services.bitcoind.RawProxy')
    def test_is_tx_valid_confirmed(self, proxy_cls_mock):
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'signrawtransaction.return_value': {
                'complete': False,
            },
            'gettransaction.return_value': {
                'confirmations': 1,
                'walletconflicts': [],
            },
        })
        tx_id = '1' * 64
        tx = Mock(**{
            'id.return_value': tx_id,
            'as_hex.return_value': 'abcd',
        })
        bc = BlockChain('BTC')
        result = bc.is_tx_valid(tx)

        self.assertIs(result, True)
        self.assertIs(proxy_mock.gettransaction.called, True)
        self.assertEqual(proxy_mock.gettransaction.call_args[0][0], tx_id)

    @patch('transactions.services.bitcoind.RawProxy')
    def test_is_tx_valid_invalid(self, proxy_cls_mock):
        proxy_cls_mock.return_value = Mock(**{
            'signrawtransaction.return_value': {
                'complete': False,
            },
            'gettransaction.return_value': {
                'confirmations': 0,
                'walletconflicts': [],
            },
        })
        tx = Mock(**{
            'id.return_value': '1' * 64,
            'as_hex.return_value': 'abcd',
        })
        bc = BlockChain('BTC')
        result = bc.is_tx_valid(tx)

        self.assertIs(result, False)

    @patch('transactions.services.bitcoind.RawProxy')
    def test_send_raw_transaction(self, proxy_cls_mock):
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'sendrawtransaction.return_value': '0' * 64,
        })
        bc = BlockChain('BTC')
        tx = Mock(**{'as_hex.return_value': 'abcd'})
        tx_id = bc.send_raw_transaction(tx)

        self.assertEqual(tx_id, '0' * 64)
        self.assertIs(proxy_mock.sendrawtransaction.called, True)
        self.assertEqual(proxy_mock.sendrawtransaction.call_args[0][0],
                         'abcd')

    @patch('transactions.services.bitcoind.RawProxy')
    def test_is_tx_confirmed_true(self, proxy_cls_mock):
        tx_id = '1' * 64
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'gettransaction.return_value': {
                'confirmations': 6,
                'walletconflicts': [],
            },
        })
        bc = BlockChain('BTC')
        self.assertIs(bc.is_tx_confirmed(tx_id), True)
        self.assertEqual(proxy_mock.gettransaction.call_count, 1)
        self.assertEqual(proxy_mock.gettransaction.call_args[0][0], tx_id)

    @patch('transactions.services.bitcoind.RawProxy')
    def test_is_tx_confirmed_false(self, proxy_cls_mock):
        tx_id = '1' * 64
        proxy_cls_mock.return_value = Mock(**{
            'gettransaction.return_value': {
                'confirmations': 1,
                'walletconflicts': [],
            },
        })
        bc = BlockChain('BTC')
        self.assertIs(bc.is_tx_confirmed(tx_id), False)

    @patch('transactions.services.bitcoind.RawProxy')
    def test_is_tx_confirmed_modified(self, proxy_cls_mock):
        tx_id_1 = '1' * 64
        tx_id_2 = '2' * 64
        proxy_cls_mock.return_value = Mock(**{
            'gettransaction.side_effect': [{
                'confirmations': 0,
                'walletconflicts': [tx_id_2],
                'vout': 'test',
            }, {
                'confirmations': 6,
                'vout': 'test',
            }],
        })
        bc = BlockChain('BTC')
        with self.assertRaises(TransactionModified) as context:
            bc.is_tx_confirmed(tx_id_1)
        self.assertEqual(context.exception.another_tx_id, tx_id_2)

    @patch('transactions.services.bitcoind.RawProxy')
    def test_is_tx_confirmed_double_spend(self, proxy_cls_mock):
        tx_id_1 = '1' * 64
        tx_id_2 = '2' * 64
        proxy_cls_mock.return_value = Mock(**{
            'gettransaction.side_effect': [{
                'confirmations': 0,
                'walletconflicts': [tx_id_2],
                'vout': 'one',
            }, {
                'confirmations': 6,
                'vout': 'two',
            }],
        })
        bc = BlockChain('BTC')
        with self.assertRaises(DoubleSpend) as context:
            bc.is_tx_confirmed(tx_id_1)
        self.assertEqual(context.exception.another_tx_id, tx_id_2)

    @patch('transactions.services.bitcoind.RawProxy')
    def test_get_tx_fee(self, proxy_cls_mock):
        proxy_cls_mock.return_value = proxy_mock = Mock(**{
            'estimatefee.return_value': Decimal('0.0002'),
        })
        bc = BlockChain('BTC')
        expected_fee = get_tx_fee(1, 1, Decimal('0.0002'))
        self.assertEqual(bc.get_tx_fee(1, 1), expected_fee)
        self.assertEqual(proxy_mock.estimatefee.call_count, 1)
        self.assertEqual(proxy_mock.estimatefee.call_args[0][0], 10)

    @patch('transactions.services.bitcoind.RawProxy')
    @override_config(TX_DEFAULT_FEE=Decimal('0.0005'))
    def test_get_tx_fee_error(self, proxy_cls_mock):
        proxy_cls_mock.return_value = Mock(**{
            'estimatefee.return_value': Decimal(-1),
        })
        bc = BlockChain('BTC')
        expected_fee = get_tx_fee(1, 1, Decimal('0.0005'))
        self.assertEqual(bc.get_tx_fee(1, 1), expected_fee)

    @patch('transactions.services.bitcoind.RawProxy')
    @override_config(TX_DEFAULT_FEE=Decimal('0.0015'))
    @override_settings(DEBUG=True)
    def test_get_tx_fee_debug(self, proxy_cls_mock):
        proxy_cls_mock.return_value = Mock(**{
            'estimatefee.return_value': Decimal('0.0009'),
        })
        bc = BlockChain('BTC')
        expected_fee = get_tx_fee(1, 1, Decimal('0.0015'))
        self.assertEqual(bc.get_tx_fee(1, 1), expected_fee)

    @patch('transactions.services.bitcoind.RawProxy')
    def test_get_tx_fee_too_small(self, proxy_cls_mock):
        proxy_cls_mock.return_value = Mock(**{
            'estimatefee.return_value': Decimal('0.00000223'),
        })
        bc = BlockChain('BTC')
        expected_fee = get_tx_fee(1, 1, BTC_MIN_FEE)
        self.assertEqual(bc.get_tx_fee(1, 1), expected_fee)


class UtilsTestCase(TestCase):

    def test_address_validation(self):
        main_addr = '1JpY93MNoeHJ914CHLCQkdhS7TvBM68Xp6'
        self.assertIsNone(
            validate_bitcoin_address(main_addr, 'BTC'))
        test_addr = 'mxqpfcxzKnPfgZw8JKs7DU6m7DTysxBBWn'
        self.assertIsNone(
            validate_bitcoin_address(test_addr, 'TBTC'))
        self.assertEqual(
            validate_bitcoin_address(test_addr, 'BTC'),
            'Invalid address for coin BTC.')
        invalid_addr = '1wFSdAv9rGpA4CvX3UtxZpUwaumsWM68pC'
        self.assertEqual(
            validate_bitcoin_address(invalid_addr, None),
            'Invalid address.')

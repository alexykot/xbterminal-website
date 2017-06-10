from decimal import Decimal

from django.test import TestCase

from mock import patch

from transactions.deposits import prepare_deposit
from wallet.constants import BIP44_COIN_TYPES
from wallet.tests.factories import WalletKeyFactory
from website.tests.factories import AccountFactory, DeviceFactory


class PrepareDepositTestCase(TestCase):

    def setUp(self):
        WalletKeyFactory()

    @patch('transactions.deposits.get_exchange_rate')
    def test_prepare_with_device(self, get_rate_mock):
        device = DeviceFactory()
        get_rate_mock.return_value = Decimal('2000.0')
        deposit = prepare_deposit(device, Decimal('10.00'))

        self.assertEqual(deposit.account, device.account)
        self.assertEqual(deposit.device, device)
        self.assertEqual(deposit.currency,
                         device.account.merchant.currency)
        self.assertEqual(deposit.amount, Decimal('10.00'))
        self.assertEqual(deposit.coin_type, BIP44_COIN_TYPES.BTC)
        self.assertIs(deposit.deposit_address.is_change, False)
        self.assertEqual(
            deposit.deposit_address.wallet_account.parent_key.coin_type,
            BIP44_COIN_TYPES.BTC)
        self.assertEqual(deposit.merchant_coin_amount, Decimal('0.005'))
        self.assertEqual(deposit.fee_coin_amount, Decimal('0.000025'))
        self.assertEqual(deposit.status, 'new')
        self.assertEqual(get_rate_mock.call_args[0][0],
                         deposit.currency.name)

    @patch('transactions.deposits.get_exchange_rate')
    def test_prepare_with_account(self, get_rate_mock):
        account = AccountFactory()
        get_rate_mock.return_value = Decimal('2000.0')
        deposit = prepare_deposit(account, Decimal('10.00'))

        self.assertEqual(deposit.account, account)
        self.assertIsNone(deposit.device)
        self.assertEqual(deposit.currency,
                         account.merchant.currency)
        self.assertEqual(deposit.coin_type, BIP44_COIN_TYPES.BTC)
        self.assertEqual(
            deposit.deposit_address.wallet_account.parent_key.coin_type,
            BIP44_COIN_TYPES.BTC)

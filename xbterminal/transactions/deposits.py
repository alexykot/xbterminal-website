from decimal import Decimal
import logging

from constance import config

from transactions.constants import BTC_DEC_PLACES, BTC_MIN_OUTPUT
from transactions.models import Deposit
from operations.services.wrappers import get_exchange_rate
from wallet.constants import BIP44_COIN_TYPES
from wallet.models import Address
from website.models import Account, Device

logger = logging.getLogger(__name__)


def _get_coin_type(account):
    """
    Determine coin type from account currency
    """
    if account.currency.name == 'BTC':
        return BIP44_COIN_TYPES.BTC
    elif account.currency.name == 'TBTC':
        return BIP44_COIN_TYPES.XTN
    else:
        raise ValueError('Instantfiat accounts are not supported.')


def prepare_deposit(device_or_account, amount):
    """
    Accepts:
        device_or_account: Device or Account instance
        amount: Decimal
    Returns:
        deposit: Deposit instance
    """
    if isinstance(device_or_account, Device):
        device = device_or_account
        account = device.account
    elif isinstance(device_or_account, Account):
        device = None
        account = device_or_account
    # Create model instance
    coin_type = _get_coin_type(account)
    deposit_address = Address.create(coin_type, is_change=False)
    deposit = Deposit(
        account=account,
        device=device,
        currency=account.merchant.currency,
        amount=amount,
        coin_type=coin_type,
        deposit_address=deposit_address)
    # Get exchange rate
    exchange_rate = get_exchange_rate(deposit.currency.name)
    # Merchant amount
    deposit.merchant_coin_amount = (deposit.amount /
                                    exchange_rate).quantize(BTC_DEC_PLACES)
    if deposit.merchant_coin_amount < BTC_MIN_OUTPUT:
        deposit.merchant_coin_amount = BTC_MIN_OUTPUT
    # Fee
    deposit.fee_coin_amount = (deposit.amount *
                               Decimal(config.OUR_FEE_SHARE) /
                               exchange_rate).quantize(BTC_DEC_PLACES)
    deposit.save()
    return deposit

from decimal import Decimal
import logging

from django.db.models import Sum
from django.db.transaction import atomic

from transactions.constants import (
    BTC_DEC_PLACES,
    BTC_MIN_OUTPUT)
from transactions.models import (
    Withdrawal,
    BalanceChange,
    get_address_balance,
    get_account_balance)
from transactions.deposits import _get_coin_type
from operations.services.wrappers import get_exchange_rate
from operations.blockchain import BlockChain
from operations.exceptions import WithdrawalError
from wallet.models import Address
from website.models import Device, Account

logger = logging.getLogger(__name__)


@atomic
def prepare_withdrawal(device_or_account, amount):
    """
    Check merchant's account balance, create withdrawal
    Accepts:
        device_or_account: Device or Account instance
        amount: Decimal
    Returns:
        withdrawal: Withdrawal instance
    """
    if isinstance(device_or_account, Device):
        device = device_or_account
        account = device.account
    elif isinstance(device_or_account, Account):
        device = None
        account = device_or_account
    if device is not None and amount > device.max_payout:
        raise WithdrawalError(
            'Amount exceeds max payout for current device')
    # Create model instance
    coin_type = _get_coin_type(account)
    withdrawal = Withdrawal(
        account=account,
        device=device,
        currency=account.merchant.currency,
        amount=amount,
        coin_type=coin_type)
    # Get exchange rate and calculate customer amount
    exchange_rate = get_exchange_rate(withdrawal.currency.name)
    withdrawal.customer_coin_amount = (withdrawal.amount / exchange_rate).\
        quantize(BTC_DEC_PLACES)
    if withdrawal.customer_coin_amount < BTC_MIN_OUTPUT:
        raise WithdrawalError('Customer coin amount is below dust threshold')
    # Find unspent outputs which are not reserved by other withdrawals
    # and check balance
    reserved_sum = Decimal(0)
    balance_changes = []
    addresses = Address.objects.\
        filter(wallet_account__parent_key__coin_type=withdrawal.coin_type).\
        annotate(balance=Sum('balancechange__amount')).\
        filter(balance__gt=0)
    bc = BlockChain(withdrawal.bitcoin_network)
    for address in addresses:
        address_balance = get_address_balance(address, only_confirmed=True)
        if address_balance == 0:
            continue
        reserved_sum += address_balance
        balance_changes.append((address, -address_balance))
        withdrawal.tx_fee_coin_amount = bc.get_tx_fee(len(balance_changes), 2)
        if reserved_sum >= withdrawal.coin_amount:
            break
    else:
        raise WithdrawalError('Insufficient balance in wallet')
    if get_account_balance(withdrawal.account, only_confirmed=True) < withdrawal.coin_amount:
        raise WithdrawalError('Insufficient balance on merchant account')
    logger.info('reserved funds on %s addresses', len(balance_changes))
    # Calculate change amount
    change_coin_amount = reserved_sum - withdrawal.coin_amount
    if change_coin_amount < BTC_MIN_OUTPUT:
        withdrawal.customer_coin_amount += change_coin_amount
    else:
        change_address = Address.create(withdrawal.coin_type, is_change=True)
        balance_changes.append((change_address, change_coin_amount))
    # Save withdrawal object and balance changes
    withdrawal.save()
    BalanceChange.objects.bulk_create([
        BalanceChange(
            withdrawal=withdrawal,
            account=withdrawal.account,
            address=address,
            amount=amount)
        for address, amount in balance_changes])  # noqa: F812
    return withdrawal

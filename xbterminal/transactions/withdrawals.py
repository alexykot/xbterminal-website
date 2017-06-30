from decimal import Decimal
import logging

from django.db.models import Sum
from django.db.transaction import atomic
from django.utils import timezone

from constance import config

from api.utils.urls import get_admin_url
from common.rq_helpers import run_periodic_task, cancel_current_task
from transactions.constants import (
    BTC_DEC_PLACES,
    BTC_MIN_OUTPUT,
    WITHDRAWAL_CONFIDENCE_TIMEOUT,
    WITHDRAWAL_CONFIRMATION_TIMEOUT)
from transactions.models import Withdrawal, BalanceChange
from transactions.utils.compat import (
    get_coin_type,
    get_address_balance,
    get_account_balance)
from transactions.utils.tx import create_tx_
from operations.services.wrappers import get_exchange_rate, is_tx_reliable
from operations.blockchain import BlockChain, validate_bitcoin_address
from operations.exceptions import (
    WithdrawalError,
    TransactionModified)
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
    coin_type = get_coin_type(account.currency.name)
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
        address_balance = get_address_balance(address, include_unconfirmed=False)
        if address_balance == 0:
            continue
        reserved_sum += address_balance
        balance_changes.append((address, -address_balance))
        withdrawal.tx_fee_coin_amount = bc.get_tx_fee(len(balance_changes), 2)
        if reserved_sum >= withdrawal.coin_amount:
            break
    else:
        raise WithdrawalError('Insufficient balance in wallet')
    if get_account_balance(withdrawal.account, include_unconfirmed=False) < withdrawal.coin_amount:
        raise WithdrawalError('Insufficient balance on merchant account')
    logger.info('reserved funds on %s addresses', len(balance_changes))
    # Calculate change amount
    change_coin_amount = reserved_sum - withdrawal.coin_amount
    if change_coin_amount < BTC_MIN_OUTPUT:
        withdrawal.customer_coin_amount += change_coin_amount
    else:
        change_address = Address.create(withdrawal.coin_type, is_change=True)
        bc.import_address(change_address.address, rescan=False)
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
    run_periodic_task(check_withdrawal_status, [withdrawal.pk], interval=60)
    return withdrawal


def send_transaction(withdrawal, customer_address):
    """
    Accepts:
        withdrawal: Withdrawal instance
        customer_address: bitcoin address, string
    """
    # Validate customer address
    error_message = validate_bitcoin_address(customer_address,
                                             withdrawal.bitcoin_network)
    if error_message:
        raise WithdrawalError(error_message)
    else:
        withdrawal.customer_address = customer_address
    # Create transaction
    tx_inputs = []
    tx_outputs = {withdrawal.customer_address: withdrawal.customer_coin_amount}
    bc = BlockChain(withdrawal.bitcoin_network)
    for bch in withdrawal.balancechange_set.all():
        if bch.amount < 0:
            # From wallet to customer
            private_key = bch.address.get_private_key()
            unspent_outputs = bc.get_raw_unspent_outputs(
                bch.address.address,
                minconf=config.TX_REQUIRED_CONFIRMATIONS)
            if sum(output['amount'] for output in unspent_outputs) != abs(bch.amount):
                raise WithdrawalError('Error in address balance')
            for output in unspent_outputs:
                tx_inputs.append(dict(output, private_key=private_key))
        else:
            # Remains in wallet
            tx_outputs[bch.address.address] = bch.amount
    outgoing_tx = create_tx_(tx_inputs, tx_outputs)
    # Send transaction, update withdrawal status
    withdrawal.outgoing_tx_id = bc.send_raw_transaction(outgoing_tx)
    withdrawal.time_sent = timezone.now()
    withdrawal.save()
    run_periodic_task(wait_for_confidence, [withdrawal.pk], interval=5)
    logger.info('withdrawal sent (%s)', withdrawal.pk)


def wait_for_confidence(withdrawal_id):
    """
    Periodic task for monitoring status of outgoing transactions
    Accepts:
        wihtdrawal_id: withdrawal ID, integer
    """
    withdrawal = Withdrawal.objects.get(pk=withdrawal_id)
    if withdrawal.time_created + WITHDRAWAL_CONFIDENCE_TIMEOUT < timezone.now():
        # Timeout, cancel job
        cancel_current_task()
    if withdrawal.time_broadcasted is not None:
        # Confidence threshold reached, cancel job
        cancel_current_task()
        return
    bc = BlockChain(withdrawal.bitcoin_network)
    try:
        tx_confirmed = bc.is_tx_confirmed(withdrawal.outgoing_tx_id, minconf=1)
    except TransactionModified as error:
        logger.warning(
            'transaction has been modified',
            extra={'data': {
                'withdrawal_admin_url': get_admin_url(withdrawal),
            }})
        withdrawal.outgoing_tx_id = error.another_tx_id
        withdrawal.save()
        return
    # If transaction is already confirmed, skip confidence check
    if tx_confirmed or is_tx_reliable(withdrawal.outgoing_tx_id,
                                      withdrawal.merchant.get_tx_confidence_threshold(),
                                      withdrawal.bitcoin_network):
        cancel_current_task()
        if withdrawal.time_broadcasted is None:
            withdrawal.time_broadcasted = timezone.now()
            withdrawal.save()
            run_periodic_task(wait_for_confirmation, [withdrawal.pk],
                              interval=15)
            logger.info('withdrawal confidence reached (%s)', withdrawal.pk)


def wait_for_confirmation(withdrawal_id):
    """
    Periodic task for confirmation monitoring
    Accepts:
        withdrawal_id: withdrawal ID, integer
    """
    withdrawal = Withdrawal.objects.get(pk=withdrawal_id)
    if withdrawal.time_created + WITHDRAWAL_CONFIRMATION_TIMEOUT < timezone.now():
        # Timeout, cancel job
        cancel_current_task()
    bc = BlockChain(withdrawal.bitcoin_network)
    try:
        tx_confirmed = bc.is_tx_confirmed(withdrawal.outgoing_tx_id)
    except TransactionModified as error:
        logger.warning(
            'transaction has been modified',
            extra={'data': {
                'withdrawal_admin_url': get_admin_url(withdrawal),
            }})
        withdrawal.outgoing_tx_id = error.another_tx_id
        withdrawal.save()
        return
    if tx_confirmed:
        cancel_current_task()
        if withdrawal.time_confirmed is None:
            withdrawal.time_confirmed = timezone.now()
            withdrawal.save()
            logger.info('withdrawal confirmed (%s)', withdrawal.pk)


def check_withdrawal_status(withdrawal_id):
    """
    Periodic task for monitoring withdrawal status
    Accepts:
        withdrawal_id: withdrawal ID, integer
    """
    with atomic():
        withdrawal = Withdrawal.objects.get(pk=withdrawal_id)
        if withdrawal.status in ['timeout', 'cancelled']:
            # Unlock reserved addresses
            withdrawal.balancechange_set.all().delete()
            cancel_current_task()
        elif withdrawal.status in ['failed', 'unconfirmed']:
            logger.error(
                'withdrawal failed (%s)',
                withdrawal.pk,
                extra={'data': {
                    'withdrawal_admin_url': get_admin_url(withdrawal),
                }})
            cancel_current_task()
        elif withdrawal.status == 'confirmed':
            # Success
            cancel_current_task()

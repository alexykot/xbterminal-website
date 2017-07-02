from decimal import Decimal
import hashlib
import random

from django.utils import timezone

from constance import config
import factory
from pycoin.encoding import hash160, hash160_sec_to_bitcoin_address
from pycoin.networks import address_prefix_for_netcode

from transactions import models
from transactions.constants import (
    BTC_DEC_PLACES,
    PAYMENT_TYPES,
    DEPOSIT_TIMEOUT,
    DEPOSIT_CONFIDENCE_TIMEOUT,
    DEPOSIT_CONFIRMATION_TIMEOUT,
    WITHDRAWAL_TIMEOUT,
    WITHDRAWAL_CONFIDENCE_TIMEOUT,
    WITHDRAWAL_CONFIRMATION_TIMEOUT)
from website.tests.factories import AccountFactory, DeviceFactory
from wallet.constants import BIP44_COIN_TYPES
from wallet.tests.factories import AddressFactory


def generate_random_address(coin_type):
    netcode = BIP44_COIN_TYPES.for_value(coin_type).constant
    randbytes = bytes(random.getrandbits(100))
    address_prefix = address_prefix_for_netcode(netcode)
    hash_ = hash160(randbytes)
    return hash160_sec_to_bitcoin_address(
        hash_, address_prefix=address_prefix)


def generate_random_tx_id():
    randbytes = bytes(random.getrandbits(100))
    return hashlib.sha256(randbytes).hexdigest()


class DepositFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.Deposit

    class Params:
        exchange_rate = factory.Faker(
            'pydecimal',
            left_digits=4,
            right_digits=2,
            positive=True)
        # Statuses
        received = factory.Trait(
            paid_coin_amount=factory.LazyAttribute(
                lambda d: d.merchant_coin_amount + d.fee_coin_amount),
            refund_address=factory.LazyAttribute(
                lambda d: generate_random_address(d.coin_type)),
            incoming_tx_ids=factory.List(
                [factory.LazyFunction(generate_random_tx_id)]),
            payment_type=PAYMENT_TYPES.BIP21,
            time_received=factory.LazyFunction(timezone.now))
        broadcasted = factory.Trait(
            received=True,
            time_broadcasted=factory.LazyFunction(timezone.now))
        notified = factory.Trait(
            broadcasted=True,
            time_notified=factory.LazyFunction(timezone.now))
        confirmed = factory.Trait(
            notified=True,
            time_confirmed=factory.LazyFunction(timezone.now))
        timeout = factory.Trait(
            time_created=factory.LazyFunction(
                lambda: timezone.now() - DEPOSIT_TIMEOUT * 2))
        failed = factory.Trait(
            received=True,
            time_created=factory.LazyFunction(
                lambda: timezone.now() - DEPOSIT_CONFIDENCE_TIMEOUT * 2),
            time_received=factory.LazyFunction(
                lambda: timezone.now() - DEPOSIT_CONFIDENCE_TIMEOUT * 2))
        unconfirmed = factory.Trait(
            received=True,
            time_created=factory.LazyFunction(
                lambda: timezone.now() - DEPOSIT_CONFIRMATION_TIMEOUT * 2),
            time_received=factory.LazyFunction(
                lambda: timezone.now() - DEPOSIT_CONFIRMATION_TIMEOUT * 2),
            time_broadcasted=factory.LazyFunction(
                lambda: timezone.now() - DEPOSIT_CONFIDENCE_TIMEOUT * 2),
            time_notified=factory.LazyFunction(
                lambda: timezone.now() - DEPOSIT_CONFIDENCE_TIMEOUT * 2))
        refunded = factory.Trait(
            failed=True,
            refund_coin_amount=factory.SelfAttribute('.paid_coin_amount'),
            refund_tx_id=factory.LazyFunction(generate_random_tx_id))
        cancelled = factory.Trait(
            time_cancelled=factory.LazyFunction(timezone.now))

    account = factory.SubFactory(AccountFactory)
    device = factory.SubFactory(
        DeviceFactory,
        merchant=factory.SelfAttribute('..account.merchant'),
        account=factory.SelfAttribute('..account'))
    currency = factory.SelfAttribute('account.merchant.currency')
    amount = factory.Faker(
        'pydecimal',
        left_digits=2,
        right_digits=2,
        positive=True)
    coin_type = BIP44_COIN_TYPES.BTC
    deposit_address = factory.SubFactory(
        AddressFactory,
        wallet_account__parent_key__coin_type=factory.SelfAttribute('....coin_type'))

    @factory.lazy_attribute
    def merchant_coin_amount(self):
        return (self.amount / self.exchange_rate).quantize(BTC_DEC_PLACES)

    @factory.lazy_attribute
    def fee_coin_amount(self):
        return (self.amount * Decimal(config.OUR_FEE_SHARE) /
                self.exchange_rate).quantize(BTC_DEC_PLACES)

    @factory.post_generation
    def time_created(self, create, extracted, **kwargs):
        if extracted:
            self.time_created = extracted
            if create:
                self.save()


class WithdrawalFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.Withdrawal

    class Params:
        exchange_rate = factory.Faker(
            'pydecimal',
            left_digits=4,
            right_digits=2,
            positive=True)
        # Statuses
        sent = factory.Trait(
            customer_address=factory.LazyAttribute(
                lambda w: generate_random_address(w.coin_type)),
            outgoing_tx_id=factory.LazyFunction(generate_random_tx_id),
            time_sent=factory.LazyFunction(timezone.now))
        broadcasted = factory.Trait(
            sent=True,
            time_broadcasted=factory.LazyFunction(timezone.now))
        notified = factory.Trait(
            broadcasted=True,
            time_notified=factory.LazyFunction(timezone.now))
        confirmed = factory.Trait(
            notified=True,
            time_confirmed=factory.LazyFunction(timezone.now))
        timeout = factory.Trait(
            time_created=factory.LazyFunction(
                lambda: timezone.now() - WITHDRAWAL_TIMEOUT * 2))
        failed = factory.Trait(
            sent=True,
            time_created=factory.LazyFunction(
                lambda: timezone.now() - WITHDRAWAL_CONFIDENCE_TIMEOUT * 2),
            time_sent=factory.LazyFunction(
                lambda: timezone.now() - WITHDRAWAL_CONFIDENCE_TIMEOUT * 2))
        unconfirmed = factory.Trait(
            notified=True,
            time_created=factory.LazyFunction(
                lambda: timezone.now() - WITHDRAWAL_CONFIRMATION_TIMEOUT * 2),
            time_sent=factory.LazyFunction(
                lambda: timezone.now() - WITHDRAWAL_CONFIRMATION_TIMEOUT * 2),
            time_broadcasted=factory.LazyFunction(
                lambda: timezone.now() - WITHDRAWAL_CONFIRMATION_TIMEOUT * 2),
            time_notified=factory.LazyFunction(
                lambda: timezone.now() - WITHDRAWAL_CONFIRMATION_TIMEOUT * 2))
        cancelled = factory.Trait(
            time_cancelled=factory.LazyFunction(timezone.now))

    account = factory.SubFactory(AccountFactory)
    device = factory.SubFactory(
        DeviceFactory,
        merchant=factory.SelfAttribute('..account.merchant'),
        account=factory.SelfAttribute('..account'))
    currency = factory.SelfAttribute('account.merchant.currency')
    amount = factory.Faker(
        'pydecimal',
        left_digits=2,
        right_digits=2,
        positive=True)
    coin_type = BIP44_COIN_TYPES.BTC
    tx_fee_coin_amount = Decimal('0.0005')

    @factory.lazy_attribute
    def customer_coin_amount(self):
        return (self.amount / self.exchange_rate).quantize(BTC_DEC_PLACES)

    @factory.post_generation
    def time_created(self, create, extracted, **kwargs):
        if extracted:
            self.time_created = extracted
            if create:
                self.save()


class BalanceChangeFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.BalanceChange

    deposit = factory.SubFactory(
        DepositFactory,
        received=True,
        fee_coin_amount=0)

    account = factory.SelfAttribute('deposit.account')
    address = factory.SelfAttribute('deposit.deposit_address')
    amount = factory.SelfAttribute('deposit.paid_coin_amount')

    @factory.post_generation
    def created_at(self, create, extracted, **kwargs):
        if extracted:
            self.created_at = extracted
            if create:
                self.save()


class NegativeBalanceChangeFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.BalanceChange

    withdrawal = factory.SubFactory(
        WithdrawalFactory,
        sent=True,
        tx_fee_coin_amount=0)

    account = factory.SelfAttribute('withdrawal.account')
    address = factory.SubFactory(
        AddressFactory,
        wallet_account__parent_key__coin_type=factory.SelfAttribute(
            '....withdrawal.coin_type'))

    @factory.lazy_attribute
    def amount(self):
        return -(self.withdrawal.customer_coin_amount +
                 self.withdrawal.tx_fee_coin_amount)

    @factory.post_generation
    def created_at(self, create, extracted, **kwargs):
        if extracted:
            self.created_at = extracted
            if create:
                self.save()

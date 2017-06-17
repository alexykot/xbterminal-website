from decimal import Decimal
import hashlib
import random

from django.utils import timezone

from constance import config
import factory
from pycoin.encoding import hash160, hash160_sec_to_bitcoin_address
from pycoin.networks import address_prefix_for_netcode

from transactions import models
from transactions.constants import BTC_DEC_PLACES, PAYMENT_TYPES
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
        received = factory.Trait(
            paid_coin_amount=factory.LazyAttribute(
                lambda d: d.merchant_coin_amount + d.fee_coin_amount),
            refund_address=factory.LazyAttribute(
                lambda d: generate_random_address(d.coin_type)),
            incoming_tx_ids=factory.List(
                [factory.LazyFunction(generate_random_tx_id)]),
            payment_type=PAYMENT_TYPES.BIP21,
            time_received=factory.LazyFunction(timezone.now))

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


class BalanceChangeFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.BalanceChange

    deposit = factory.SubFactory(DepositFactory, received=True)

    account = factory.SelfAttribute('deposit.account')
    address = factory.SelfAttribute('deposit.deposit_address')
    amount = factory.SelfAttribute('deposit.paid_coin_amount')
from decimal import Decimal

from constance import config
import factory

from transactions import models
from transactions.constants import BTC_DEC_PLACES
from website.tests.factories import AccountFactory, DeviceFactory
from wallet.constants import BIP44_COIN_TYPES
from wallet.tests.factories import AddressFactory


class DepositFactory(factory.DjangoModelFactory):

    class Meta:
        model = models.Deposit

    class Params:
        exchange_rate = factory.Faker(
            'pydecimal',
            left_digits=4,
            right_digits=2,
            positive=True)

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

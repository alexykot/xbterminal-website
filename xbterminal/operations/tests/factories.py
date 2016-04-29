from decimal import Decimal
import uuid

from bitcoin.core import COutPoint
import factory
from factory import fuzzy

from website.tests.factories import DeviceFactory, TransactionFactory
from operations.models import PaymentOrder, WithdrawalOrder
from operations import BTC_DEC_PLACES
from operations.blockchain import serialize_outputs


class PaymentOrderFactory(factory.DjangoModelFactory):

    class Meta:
        model = PaymentOrder

    device = factory.SubFactory(DeviceFactory)
    bitcoin_network = factory.LazyAttribute(
        lambda po: po.device.bitcoin_network)
    local_address = '1PZoCJdbQdYsBur25F6cZLejM1bkSSUktL'
    merchant_address = '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'
    fee_address = '1NdS5JCXzbhNv4STQAaknq56iGstfgRCXg'
    fiat_currency = factory.LazyAttribute(
        lambda po: po.device.merchant.currency)

    fiat_amount = fuzzy.FuzzyDecimal(0.1, 2.0)
    instantfiat_fiat_amount = Decimal(0)
    instantfiat_btc_amount = Decimal(0)
    merchant_btc_amount = factory.LazyAttribute(
        lambda po: (po.fiat_amount / 400).quantize(BTC_DEC_PLACES))
    fee_btc_amount = Decimal(0)
    tx_fee_btc_amount = Decimal('0.0001')

    @factory.post_generation
    def account_tx(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted is True:
            self.account_tx = TransactionFactory.create(
                account=self.device.account,
                amount=self.merchant_btc_amount)
        else:
            self.account_tx = extracted
        self.save()

    @factory.post_generation
    def time_created(self, create, extracted, **kwargs):
        if extracted:
            self.time_created = extracted
            if create:
                self.save()


class WithdrawalOrderFactory(factory.DjangoModelFactory):

    class Meta:
        model = WithdrawalOrder

    device = factory.SubFactory(DeviceFactory)
    bitcoin_network = factory.LazyAttribute(
        lambda wo: wo.device.bitcoin_network)
    merchant_address = '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'
    fiat_currency = factory.LazyAttribute(
        lambda wo: wo.device.merchant.currency)
    fiat_amount = fuzzy.FuzzyDecimal(0.1, 2.0)
    customer_btc_amount = factory.LazyAttribute(
        lambda wo: (wo.fiat_amount / wo.exchange_rate).quantize(BTC_DEC_PLACES))
    tx_fee_btc_amount = Decimal('0.0001')
    change_btc_amount = Decimal(0)
    exchange_rate = Decimal('220')

    @factory.post_generation
    def account_tx(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted is True:
            self.account_tx = TransactionFactory.create(
                account=self.device.account,
                amount=-self.btc_amount)
        else:
            self.account_tx = extracted
        self.save()

    @factory.post_generation
    def time_created(self, create, extracted, **kwargs):
        if extracted:
            self.time_created = extracted
            if create:
                self.save()

    @factory.post_generation
    def reserved_outputs(self, create, extracted, **kwargs):
        self.reserved_outputs = serialize_outputs(extracted or [])


def outpoint_factory():
    hsh = uuid.uuid4().bytes * 2
    return COutPoint(hash=hsh, n=1)

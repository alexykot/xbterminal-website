from decimal import Decimal
from django.utils import timezone
import factory

from website.models import (
    User,
    MerchantAccount,
    BTCAccount,
    Device,
    PaymentOrder)


class UserFactory(factory.DjangoModelFactory):

    class Meta:
        model = User

    email = factory.Sequence(lambda n: 'user_{0}@xbterminal.io'.format(n))
    password = factory.PostGenerationMethodCall('set_password', 'password')


class MerchantAccountFactory(factory.DjangoModelFactory):

    class Meta:
        model = MerchantAccount

    user = factory.SubFactory(UserFactory)
    company_name = factory.Sequence(lambda n: 'Company {0}'.format(n))
    trading_name = factory.LazyAttribute(lambda ma: ma.company_name)

    business_address = 'Test Address, 123'
    town = 'London'
    post_code = 'ABC 123'
    country = 'GB'

    contact_first_name = 'Test'
    contact_last_name = 'Test'
    contact_phone = '+123456789'
    contact_email = factory.LazyAttribute(lambda ma: ma.user.email)


class BTCAccountFactory(factory.DjangoModelFactory):

    class Meta:
        model = BTCAccount

    merchant = factory.SubFactory(MerchantAccountFactory)


class DeviceFactory(factory.DjangoModelFactory):

    class Meta:
        model = Device

    merchant = factory.SubFactory(MerchantAccountFactory)
    device_type = 'hardware'
    name = factory.Sequence(lambda n: 'Terminal #{0}'.format(n))
    percent = 0
    bitcoin_address = '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'


class PaymentOrderFactory(factory.DjangoModelFactory):

    class Meta:
        model = PaymentOrder

    device = factory.SubFactory(DeviceFactory)

    local_address = '1PZoCJdbQdYsBur25F6cZLejM1bkSSUktL'
    merchant_address = '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'
    fee_address = '1NdS5JCXzbhNv4STQAaknq56iGstfgRCXg'
    fiat_currency = 'GBP'

    fiat_amount = Decimal(1.11)
    instantfiat_fiat_amount = Decimal(0)
    instantfiat_btc_amount = Decimal(0)
    merchant_btc_amount = Decimal('0.00476722')
    fee_btc_amount = Decimal(0)
    btc_amount = Decimal('0.00486722')
    effective_exchange_rate = Decimal('228.05626210')

    time_created = factory.LazyAttribute(lambda po: timezone.now())

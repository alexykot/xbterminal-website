import datetime
import hashlib
import uuid

import factory
from faker import Faker

from oauth2_provider.models import Application
from website.models import (
    Currency,
    User,
    MerchantAccount,
    Account,
    DeviceBatch,
    Device,
    ReconciliationTime,
    INSTANTFIAT_PROVIDERS)

fake = Faker()


class CurrencyFactory(factory.DjangoModelFactory):

    class Meta:
        model = Currency

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.objects.get(
            name=kwargs.get('name', 'GBP'))


class UserFactory(factory.DjangoModelFactory):

    class Meta:
        model = User

    email = factory.Sequence(lambda n: 'user_{0}@xbterminal.io'.format(n))
    password = factory.PostGenerationMethodCall('set_password', 'password')

    @factory.post_generation
    def oauth_app(self, create, extracted, **kwargs):
        if create:
            Application.objects.create(
                user=self,
                name='XBTerminal test app',
                client_id=self.email,
                client_type='confidential',
                authorization_grant_type='password',
                client_secret='secret')


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


class AccountFactory(factory.DjangoModelFactory):

    class Meta:
        model = Account

    merchant = factory.SubFactory(MerchantAccountFactory)
    currency = factory.SubFactory(CurrencyFactory, name='BTC')

    @factory.lazy_attribute
    def instantfiat_provider(self):
        if self.currency.name not in ['BTC', 'TBTC']:
            return INSTANTFIAT_PROVIDERS.CRYPTOPAY

    @factory.lazy_attribute
    def instantfiat_api_key(self):
        if self.currency.name not in ['BTC', 'TBTC']:
            return fake.sha256(raw_output=False)


class DeviceBatchFactory(factory.DjangoModelFactory):

    class Meta:
        model = DeviceBatch

    size = 10


class DeviceFactory(factory.DjangoModelFactory):

    class Meta:
        model = Device

    merchant = factory.SubFactory(MerchantAccountFactory)
    account = factory.SubFactory(
        AccountFactory,
        merchant=factory.SelfAttribute('..merchant'))
    device_type = 'hardware'
    name = factory.Sequence(lambda n: 'Terminal #{0}'.format(n))

    @factory.lazy_attribute
    def bitcoin_address(self):
        if self.account.currency.name in ['BTC', 'TBTC']:
            return '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'

    @factory.post_generation
    def status(self, create, extracted, **kwargs):
        if not extracted or extracted == 'active':
            self.start_activation()
            self.activate()
        elif extracted == 'registered':
            self.merchant = None
            self.account = None
        elif extracted == 'activation':
            self.start_activation()
        elif extracted == 'suspended':
            self.start_activation()
            self.activate()
            self.suspend()
        if create:
            self.save()

    @factory.post_generation
    def long_key(self, created, extracted, **kwargs):
        if extracted:
            self.key = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
            if created:
                self.save()


class ReconciliationTimeFactory(factory.DjangoModelFactory):

    class Meta:
        model = ReconciliationTime

    device = factory.SubFactory(DeviceFactory)
    email = factory.LazyAttribute(lambda rt: rt.device.merchant.user.email)
    time = datetime.time(10, 0)

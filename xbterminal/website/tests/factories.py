import datetime
import hashlib
import StringIO
import tempfile
import uuid
from contextlib import contextmanager

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
import factory
from factory import fuzzy
from faker import Faker
from PIL import Image

from oauth2_provider.models import Application
from website.models import (
    Currency,
    User,
    MerchantAccount,
    KYCDocument,
    Account,
    Transaction,
    DeviceBatch,
    Device,
    ReconciliationTime,
    INSTANTFIAT_PROVIDERS)

fake = Faker()


@contextmanager
def create_image(size=100):
    """
    Context manager
    Yields image o the given size (as bytes)
    """
    image = Image.frombytes('L', (size, size), '\x00' * size * size)
    tmp_file = tempfile.NamedTemporaryFile(suffix='.jpg',
                                           dir=settings.TEMP_DIR)
    image.save(tmp_file)
    tmp_file.seek(0)
    yield tmp_file
    tmp_file.close()


def create_uploaded_image(size=100, name='test.png'):
    """
    Creates in-memory uploaded PNG image
    """
    buffer = StringIO.StringIO()
    image = Image.frombytes('L', (size, size), '\x00' * size * size)
    image.save(buffer, 'PNG')
    file = InMemoryUploadedFile(buffer, None, name, 'image/png',
                                buffer.len, None)
    file.seek(0)
    return file


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

    currency = factory.SubFactory(CurrencyFactory)


class KYCDocumentFactory(factory.DjangoModelFactory):

    class Meta:
        model = KYCDocument

    merchant = factory.SubFactory(MerchantAccountFactory)
    document_type = KYCDocument.IDENTITY_DOCUMENT

    @factory.post_generation
    def file(self, create, extracted, **kwargs):
        size = kwargs.get('size', 100)
        name = kwargs.get('name', 'test.png')
        image = create_uploaded_image(size=size, name=name)
        self.file.field.save_form_data(self, image)
        if create:
            self.save()


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

    @factory.post_generation
    def balance(self, create, extracted, **kwargs):
        if create and extracted:
            self.transaction_set.create(amount=extracted)


class TransactionFactory(factory.DjangoModelFactory):

    class Meta:
        model = Transaction

    account = factory.SubFactory(AccountFactory)
    amount = fuzzy.FuzzyDecimal(0.01, 0.95)


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

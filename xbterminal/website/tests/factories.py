import factory

from website.models import User, MerchantAccount, Device


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


class DeviceFactory(factory.DjangoModelFactory):

    class Meta:
        model = Device

    merchant = factory.SubFactory(MerchantAccountFactory)
    device_type = 'hardware'
    name = factory.Sequence(lambda n: 'Terminal #{0}'.format(n))
    percent = 0
    bitcoin_address = '1PWVL1fW7Ysomg9rXNsS8ng5ZzURa2p9vE'

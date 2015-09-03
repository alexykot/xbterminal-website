# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import website.models
import django_countries.fields
import website.files
import website.validators
from django.conf import settings
import django.utils.timezone
import django.core.files.storage


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('email', models.EmailField(unique=True, max_length=254)),
                ('is_staff', models.BooleanField(default=False, help_text=b'Designates whether the user can log into this admin site.', verbose_name=b'staff status')),
                ('is_active', models.BooleanField(default=True, help_text=b'Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name=b'active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
                ('groups', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of his/her group.', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Permission', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BTCAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('network', models.CharField(default=b'mainnet', max_length=50, choices=[(b'mainnet', b'Main'), (b'testnet', b'Testnet')])),
                ('balance', models.DecimalField(default=0, max_digits=20, decimal_places=8)),
                ('balance_max', models.DecimalField(default=0, max_digits=20, decimal_places=8)),
                ('address', models.CharField(blank=True, max_length=35, null=True, validators=[website.validators.validate_bitcoin_address])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('postfix', models.CharField(default=b'', max_length=50)),
                ('prefix', models.CharField(default=b'', max_length=50)),
            ],
            options={
                'verbose_name_plural': 'currencies',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('device_type', models.CharField(max_length=50, choices=[(b'hardware', 'Terminal'), (b'mobile', 'Mobile app'), (b'web', 'Web app')])),
                ('status', models.CharField(default=b'active', max_length=50, choices=[(b'preordered', 'Preordered'), (b'dispatched', 'Dispatched'), (b'delivered', 'Delivered'), (b'active', 'Operational'), (b'suspended', 'Suspended'), (b'disposed', 'Disposed')])),
                ('name', models.CharField(max_length=100, verbose_name='Your reference')),
                ('percent', models.DecimalField(default=100, verbose_name='Percent to convert', max_digits=4, decimal_places=1, validators=[website.validators.validate_percent])),
                ('bitcoin_address', models.CharField(max_length=100, verbose_name='Bitcoin address to send to', blank=True)),
                ('key', models.CharField(default=website.models.gen_device_key, verbose_name='Device key', unique=True, max_length=32, editable=False)),
                ('serial_number', models.CharField(max_length=50, null=True, blank=True)),
                ('bitcoin_network', models.CharField(default=b'mainnet', max_length=50, choices=[(b'mainnet', b'Main'), (b'testnet', b'Testnet')])),
                ('last_activity', models.DateTimeField(null=True, blank=True)),
                ('last_reconciliation', models.DateTimeField(auto_now_add=True)),
                ('our_fee_override', models.CharField(max_length=50, null=True, blank=True)),
                ('api_key', models.TextField(help_text=b'API public key', null=True, blank=True)),
            ],
            options={
                'ordering': ['id'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='KYCDocument',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('document_type', models.IntegerField(choices=[(1, b'IdentityDocument'), (2, b'CorporateDocument')])),
                ('file', models.FileField(storage=django.core.files.storage.FileSystemStorage(base_url=b'/verification/', location=b'media/verification'), upload_to=website.files.verification_file_path_gen)),
                ('uploaded', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(default=b'uploaded', max_length=50, choices=[(b'uploaded', 'Uploaded'), (b'unverified', 'Unverified'), (b'denied', 'Denied'), (b'verified', 'Verified')])),
                ('gocoin_document_id', models.CharField(max_length=36, null=True, blank=True)),
                ('comment', models.CharField(max_length=255, null=True, blank=True)),
            ],
            options={
                'verbose_name': 'KYC document',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('code', models.CharField(unique=True, max_length=2)),
                ('fractional_split', models.CharField(default=b'.', max_length=1)),
                ('thousands_split', models.CharField(default=b',', max_length=1)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MerchantAccount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('company_name', models.CharField(unique=True, max_length=255, verbose_name='Company name')),
                ('trading_name', models.CharField(max_length=255, verbose_name='Trading name', blank=True)),
                ('business_address', models.CharField(max_length=255, null=True, verbose_name='Business address')),
                ('business_address1', models.CharField(default=b'', max_length=255, verbose_name=b'', blank=True)),
                ('business_address2', models.CharField(default=b'', max_length=255, verbose_name=b'', blank=True)),
                ('town', models.CharField(max_length=64, null=True, verbose_name='Town')),
                ('county', models.CharField(default=b'', max_length=128, verbose_name='State / County', blank=True)),
                ('post_code', models.CharField(max_length=32, null=True, verbose_name='Post code', validators=[website.validators.validate_post_code])),
                ('country', django_countries.fields.CountryField(default=b'GB', max_length=2, verbose_name='Country')),
                ('contact_first_name', models.CharField(max_length=255, verbose_name='Contact first name')),
                ('contact_last_name', models.CharField(max_length=255, verbose_name='Contact last name')),
                ('contact_phone', models.CharField(max_length=32, null=True, verbose_name='Contact phone', validators=[website.validators.validate_phone])),
                ('contact_email', models.EmailField(unique=True, max_length=254, verbose_name='Contact email')),
                ('payment_processor', models.CharField(default=b'gocoin', max_length=50, verbose_name='Payment processor', choices=[(b'bitpay', b'BitPay'), (b'cryptopay', b'CryptoPay'), (b'gocoin', b'GoCoin')])),
                ('api_key', models.CharField(max_length=255, verbose_name='API key', blank=True)),
                ('gocoin_merchant_id', models.CharField(max_length=36, null=True, blank=True)),
                ('verification_status', models.CharField(default=b'unverified', max_length=50, verbose_name='KYC', choices=[(b'unverified', 'unverified'), (b'pending', 'verification pending'), (b'verified', 'verified')])),
                ('comments', models.TextField(blank=True)),
                ('currency', models.ForeignKey(default=1, to='website.Currency')),
                ('language', models.ForeignKey(default=1, to='website.Language')),
                ('user', models.OneToOneField(related_name='merchant', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('quantity', models.IntegerField()),
                ('payment_method', models.CharField(default=b'bitcoin', max_length=50, choices=[(b'bitcoin', 'Bitcoin'), (b'wire', 'Bank wire transfer')])),
                ('fiat_total_amount', models.DecimalField(max_digits=20, decimal_places=8)),
                ('delivery_address', models.CharField(max_length=255, blank=True)),
                ('delivery_address1', models.CharField(max_length=255, verbose_name=b'', blank=True)),
                ('delivery_address2', models.CharField(max_length=255, verbose_name=b'', blank=True)),
                ('delivery_town', models.CharField(max_length=64, blank=True)),
                ('delivery_county', models.CharField(max_length=128, blank=True)),
                ('delivery_post_code', models.CharField(blank=True, max_length=32, validators=[website.validators.validate_post_code])),
                ('delivery_country', django_countries.fields.CountryField(default=b'GB', max_length=2, blank=True)),
                ('delivery_contact_phone', models.CharField(max_length=32, blank=True)),
                ('instantfiat_invoice_id', models.CharField(max_length=255, null=True)),
                ('instantfiat_btc_total_amount', models.DecimalField(null=True, max_digits=18, decimal_places=8)),
                ('instantfiat_address', models.CharField(max_length=35, null=True, validators=[website.validators.validate_bitcoin_address])),
                ('payment_reference', models.CharField(default=website.models.gen_payment_reference, unique=True, max_length=10, editable=False)),
                ('payment_status', models.CharField(default=b'unpaid', max_length=50, choices=[(b'unpaid', b'unpaid'), (b'paid', b'paid')])),
                ('merchant', models.ForeignKey(to='website.MerchantAccount')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PaymentOrder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uid', models.CharField(default=website.models.gen_payment_uid, verbose_name=b'UID', unique=True, max_length=32, editable=False)),
                ('request', models.BinaryField()),
                ('local_address', models.CharField(max_length=35, validators=[website.validators.validate_bitcoin_address])),
                ('merchant_address', models.CharField(max_length=35, validators=[website.validators.validate_bitcoin_address])),
                ('fee_address', models.CharField(max_length=35, validators=[website.validators.validate_bitcoin_address])),
                ('instantfiat_address', models.CharField(max_length=35, null=True, validators=[website.validators.validate_bitcoin_address])),
                ('refund_address', models.CharField(max_length=35, null=True, validators=[website.validators.validate_bitcoin_address])),
                ('fiat_currency', models.CharField(max_length=3)),
                ('fiat_amount', models.DecimalField(max_digits=20, decimal_places=8)),
                ('instantfiat_fiat_amount', models.DecimalField(max_digits=9, decimal_places=2)),
                ('instantfiat_btc_amount', models.DecimalField(max_digits=18, decimal_places=8)),
                ('merchant_btc_amount', models.DecimalField(max_digits=18, decimal_places=8)),
                ('fee_btc_amount', models.DecimalField(max_digits=18, decimal_places=8)),
                ('extra_btc_amount', models.DecimalField(default=0, max_digits=18, decimal_places=8)),
                ('btc_amount', models.DecimalField(max_digits=20, decimal_places=8)),
                ('effective_exchange_rate', models.DecimalField(max_digits=20, decimal_places=8)),
                ('instantfiat_invoice_id', models.CharField(max_length=255, null=True)),
                ('incoming_tx_id', models.CharField(max_length=64, null=True, validators=[website.validators.validate_transaction])),
                ('outgoing_tx_id', models.CharField(max_length=64, null=True, validators=[website.validators.validate_transaction])),
                ('payment_type', models.CharField(max_length=10, choices=[(b'bip0021', 'BIP 0021 (Bitcoin URI)'), (b'bip0070', 'BIP 0070 (Payment Protocol)')])),
                ('time_created', models.DateTimeField()),
                ('time_recieved', models.DateTimeField(null=True)),
                ('time_forwarded', models.DateTimeField(null=True)),
                ('time_broadcasted', models.DateTimeField(null=True)),
                ('time_exchanged', models.DateTimeField(null=True)),
                ('time_finished', models.DateTimeField(null=True)),
                ('receipt_key', models.CharField(max_length=32, unique=True, null=True)),
                ('device', models.ForeignKey(to='website.Device')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ReconciliationTime',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=254)),
                ('time', models.TimeField()),
                ('device', models.ForeignKey(related_name='rectime_set', to='website.Device')),
            ],
            options={
                'ordering': ['time'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='WithdrawalOrder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uid', models.CharField(default=website.models.gen_withdrawal_uid, verbose_name=b'UID', unique=True, max_length=32, editable=False)),
                ('bitcoin_network', models.CharField(max_length=10, choices=[(b'mainnet', b'Main'), (b'testnet', b'Testnet')])),
                ('merchant_address', models.CharField(max_length=35, validators=[website.validators.validate_bitcoin_address])),
                ('customer_address', models.CharField(max_length=35, null=True, validators=[website.validators.validate_bitcoin_address])),
                ('fiat_amount', models.DecimalField(max_digits=12, decimal_places=2)),
                ('customer_btc_amount', models.DecimalField(max_digits=18, decimal_places=8)),
                ('tx_fee_btc_amount', models.DecimalField(max_digits=18, decimal_places=8)),
                ('change_btc_amount', models.DecimalField(max_digits=18, decimal_places=8)),
                ('exchange_rate', models.DecimalField(max_digits=18, decimal_places=8)),
                ('reserved_outputs', models.BinaryField()),
                ('outgoing_tx_id', models.CharField(max_length=64, null=True, validators=[website.validators.validate_transaction])),
                ('time_created', models.DateTimeField(auto_now_add=True)),
                ('time_sent', models.DateTimeField(null=True)),
                ('time_broadcasted', models.DateTimeField(null=True)),
                ('time_completed', models.DateTimeField(null=True)),
                ('device', models.ForeignKey(to='website.Device')),
                ('fiat_currency', models.ForeignKey(to='website.Currency')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='kycdocument',
            name='merchant',
            field=models.ForeignKey(to='website.MerchantAccount'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='device',
            name='merchant',
            field=models.ForeignKey(to='website.MerchantAccount'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='btcaccount',
            name='merchant',
            field=models.ForeignKey(to='website.MerchantAccount'),
            preserve_default=True,
        ),
    ]

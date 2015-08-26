# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_countries.fields
import website.validators
import operations.models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0003_schema_move_models'),
    ]

    state_operations = [
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
                ('payment_reference', models.CharField(default=operations.models.gen_payment_reference, unique=True, max_length=10, editable=False)),
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
                ('uid', models.CharField(default=operations.models.gen_payment_uid, verbose_name=b'UID', unique=True, max_length=32, editable=False)),
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
            name='WithdrawalOrder',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uid', models.CharField(default=operations.models.gen_withdrawal_uid, verbose_name=b'UID', unique=True, max_length=32, editable=False)),
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
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=state_operations)
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0048_data_cryptopay_accounts'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='merchantaccount',
            name='api_key',
        ),
        migrations.RemoveField(
            model_name='merchantaccount',
            name='gocoin_merchant_id',
        ),
        migrations.RemoveField(
            model_name='merchantaccount',
            name='payment_processor',
        ),
        migrations.AddField(
            model_name='merchantaccount',
            name='instantfiat_api_key',
            field=models.CharField(max_length=200, null=True, verbose_name='InstantFiat API key', blank=True),
        ),
        migrations.AddField(
            model_name='merchantaccount',
            name='instantfiat_merchant_id',
            field=models.CharField(max_length=50, null=True, verbose_name='InstantFiat merchant ID', blank=True),
        ),
        migrations.AddField(
            model_name='merchantaccount',
            name='instantfiat_provider',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='InstantFiat provider', choices=[(1, b'CryptoPay'), (2, b'GoCoin')]),
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0033_schema_account_rename_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='instantfiat_api_key',
            field=models.CharField(max_length=200, null=True, verbose_name='InstantFiat API key', blank=True),
        ),
        migrations.AddField(
            model_name='account',
            name='instantfiat_provider',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='InstantFiat provider', choices=[(1, b'CryptoPay')]),
        ),
    ]

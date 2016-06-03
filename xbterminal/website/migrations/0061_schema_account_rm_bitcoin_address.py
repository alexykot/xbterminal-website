# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0060_data_create_addresses'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='bitcoin_address',
        ),
        migrations.AlterField(
            model_name='account',
            name='instantfiat_account_id',
            field=models.CharField(max_length=50, null=True, verbose_name='InstantFiat account ID', blank=True),
        ),
    ]

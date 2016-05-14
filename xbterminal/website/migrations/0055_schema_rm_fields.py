# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0054_schema_merchant_can_activate'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='instantfiat_api_key',
        ),
        migrations.RemoveField(
            model_name='account',
            name='instantfiat_merchant_id',
        ),
        migrations.RemoveField(
            model_name='account',
            name='instantfiat_provider',
        ),
        migrations.RemoveField(
            model_name='device',
            name='bitcoin_address',
        ),
        migrations.RemoveField(
            model_name='device',
            name='serial_number',
        ),
    ]

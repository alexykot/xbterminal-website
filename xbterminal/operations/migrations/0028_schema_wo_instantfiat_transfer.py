# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import website.validators


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0027_schema_order_rm_account_tx'),
    ]

    operations = [
        migrations.AddField(
            model_name='withdrawalorder',
            name='instantfiat_reference',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='withdrawalorder',
            name='instantfiat_transfer_id',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='withdrawalorder',
            name='merchant_address',
            field=models.CharField(max_length=35, null=True, validators=[website.validators.validate_bitcoin_address]),
        ),
    ]

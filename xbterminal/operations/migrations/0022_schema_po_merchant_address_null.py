# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import website.validators


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0021_schema_po_time_cancelled'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentorder',
            name='merchant_address',
            field=models.CharField(max_length=35, null=True, validators=[website.validators.validate_bitcoin_address]),
        ),
    ]

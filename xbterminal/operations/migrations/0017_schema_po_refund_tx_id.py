# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import website.validators


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0016_schema_po_time_notified'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentorder',
            name='refund_tx_id',
            field=models.CharField(max_length=64, null=True, validators=[website.validators.validate_transaction]),
        ),
        migrations.AddField(
            model_name='paymentorder',
            name='time_refunded',
            field=models.DateTimeField(null=True),
        ),
    ]

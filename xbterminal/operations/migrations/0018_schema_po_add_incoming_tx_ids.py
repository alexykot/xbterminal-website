# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.contrib.postgres.fields
import website.validators


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0017_schema_po_refund_tx_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentorder',
            name='incoming_tx_ids',
            field=django.contrib.postgres.fields.ArrayField(default=list, base_field=models.CharField(max_length=64, validators=[website.validators.validate_transaction]), size=None),
        ),
    ]

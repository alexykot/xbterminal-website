# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0005_schema_po_remove_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentorder',
            name='tx_fee_btc_amount',
            field=models.DecimalField(null=True, max_digits=18, decimal_places=8),
            preserve_default=True,
        ),
    ]

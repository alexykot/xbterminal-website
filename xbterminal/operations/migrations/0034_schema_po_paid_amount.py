# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0033_schema_po_fix_fiat_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentorder',
            name='paid_btc_amount',
            field=models.DecimalField(default=0, max_digits=18, decimal_places=8),
        ),
    ]

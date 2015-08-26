# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0007_data_po_tx_fee_btc_amount'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentorder',
            name='tx_fee_btc_amount',
            field=models.DecimalField(max_digits=18, decimal_places=8),
            preserve_default=True,
        ),
    ]

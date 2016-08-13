# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0032_schema_po_remove_request'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentorder',
            name='fiat_amount',
            field=models.DecimalField(max_digits=12, decimal_places=2),
        ),
    ]

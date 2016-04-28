# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0022_schema_po_merchant_address_null'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentorder',
            name='btc_amount',
        ),
    ]

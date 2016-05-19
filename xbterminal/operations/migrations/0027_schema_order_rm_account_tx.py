# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0026_data_transaction_order_fk'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentorder',
            name='account_tx',
        ),
        migrations.RemoveField(
            model_name='withdrawalorder',
            name='account_tx',
        ),
    ]

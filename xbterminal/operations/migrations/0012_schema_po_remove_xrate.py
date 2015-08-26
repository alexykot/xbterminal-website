# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0011_schema_po_bitcoin_network_nn'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentorder',
            name='effective_exchange_rate',
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0019_data_po_copy_incoming_tx_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentorder',
            name='incoming_tx_id',
        ),
    ]

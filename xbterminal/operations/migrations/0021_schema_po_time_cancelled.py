# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0020_schema_po_remove_incoming_tx_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentorder',
            name='time_cancelled',
            field=models.DateTimeField(null=True),
        ),
    ]

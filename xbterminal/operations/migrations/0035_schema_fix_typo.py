# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0034_schema_po_paid_amount'),
    ]

    operations = [
        migrations.RenameField(
            model_name='paymentorder',
            old_name='time_recieved',
            new_name='time_received',
        ),
    ]

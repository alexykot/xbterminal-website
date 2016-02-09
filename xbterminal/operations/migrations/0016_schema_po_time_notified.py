# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0015_schema_po_time_confirmed'),
    ]

    operations = [
        migrations.RenameField(
            model_name='paymentorder',
            old_name='time_finished',
            new_name='time_notified',
        ),
    ]

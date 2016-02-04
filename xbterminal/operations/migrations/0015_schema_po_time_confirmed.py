# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0014_schema_wo_time_cancelled'),
    ]

    operations = [
        migrations.RenameField(
            model_name='paymentorder',
            old_name='time_broadcasted',
            new_name='time_confirmed',
        ),
    ]

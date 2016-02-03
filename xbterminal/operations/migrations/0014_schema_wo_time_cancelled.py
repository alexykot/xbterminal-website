# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0013_schema_remove_receipt_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='withdrawalorder',
            name='time_cancelled',
            field=models.DateTimeField(null=True),
        ),
    ]

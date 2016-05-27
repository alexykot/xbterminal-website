# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0031_schema_order_device_null'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentorder',
            name='request',
        ),
    ]

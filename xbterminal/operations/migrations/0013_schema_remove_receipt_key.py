# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0012_schema_po_remove_xrate'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentorder',
            name='receipt_key',
        ),
    ]

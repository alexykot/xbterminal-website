# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0040_schema_device_rm_bitcoin_network'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='device',
            name='percent',
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0022_schema_default_device_status'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='device',
            options={'ordering': ['-id']},
        ),
    ]

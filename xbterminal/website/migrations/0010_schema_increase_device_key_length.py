# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import website.models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0009_schema_set_default_batch'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='key',
            field=models.CharField(default=website.models.gen_device_key, verbose_name='Device key', unique=True, max_length=64, editable=False),
            preserve_default=True,
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import website.models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0008_schema_device_batch_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='batch',
            field=models.ForeignKey(default=website.models.get_default_batch, to='website.DeviceBatch'),
            preserve_default=True,
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import website.models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0005_schema_device_batch'),
    ]

    operations = [
        migrations.AlterField(
            model_name='devicebatch',
            name='batch_number',
            field=models.CharField(default=website.models.gen_batch_number, unique=True, max_length=32, editable=False),
            preserve_default=True,
        ),
    ]

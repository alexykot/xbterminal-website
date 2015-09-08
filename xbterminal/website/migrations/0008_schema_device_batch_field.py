# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0007_data_create_batches'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='batch',
            field=models.ForeignKey(to='website.DeviceBatch', null=True),
            preserve_default=True,
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0036_data_device_no_partial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='bitcoin_address',
            field=models.CharField(max_length=100, null=True, verbose_name='Bitcoin address to send to', blank=True),
        ),
    ]

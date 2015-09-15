# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0016_data_activation_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='activation_code',
            field=models.CharField(unique=True, max_length=6, editable=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='device',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
            preserve_default=True,
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0014_schema_device_upd_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='activation_code',
            field=models.CharField(max_length=6, unique=True, null=True, editable=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='device',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
            preserve_default=True,
        ),
    ]

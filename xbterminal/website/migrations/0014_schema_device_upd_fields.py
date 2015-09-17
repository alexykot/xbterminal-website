# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import website.models
import website.validators


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0013_schema_device_merchant_null'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='api_key',
            field=models.TextField(blank=True, help_text=b'API public key', null=True, validators=[website.validators.validate_public_key]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='device',
            name='key',
            field=models.CharField(default=website.models.gen_device_key, unique=True, max_length=64, verbose_name='Device key'),
            preserve_default=True,
        ),
    ]

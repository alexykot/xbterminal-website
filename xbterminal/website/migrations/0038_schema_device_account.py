# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0037_schema_device_bitcoin_address_null'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='account',
            field=models.ForeignKey(blank=True, to='website.Account', null=True),
        ),
    ]

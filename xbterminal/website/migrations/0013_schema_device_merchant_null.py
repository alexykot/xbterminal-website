# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0012_schema_device_statuses'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='merchant',
            field=models.ForeignKey(blank=True, to='website.MerchantAccount', null=True),
            preserve_default=True,
        ),
    ]

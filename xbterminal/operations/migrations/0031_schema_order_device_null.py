# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0030_data_accounts'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentorder',
            name='device',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='website.Device', null=True),
        ),
        migrations.AlterField(
            model_name='withdrawalorder',
            name='device',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to='website.Device', null=True),
        ),
    ]

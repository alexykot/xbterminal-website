# -*- coding: utf-8 -*-
# Generated by Django 1.9.12 on 2017-02-28 11:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0082_schema_device_sysinfo_blank'),
    ]

    operations = [
        migrations.AddField(
            model_name='currency',
            name='max_payout',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=20, verbose_name='Maximum payout'),
        ),
    ]

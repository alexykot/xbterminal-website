# -*- coding: utf-8 -*-
# Generated by Django 1.9.12 on 2017-02-28 15:06
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0085_data_device_max_payout'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='max_payout',
        ),
    ]

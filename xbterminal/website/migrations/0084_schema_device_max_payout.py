# -*- coding: utf-8 -*-
# Generated by Django 1.9.12 on 2017-02-28 12:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0083_schema_currency_max_payout'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='max_payout',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True, verbose_name='Maximum payout'),
        ),
    ]

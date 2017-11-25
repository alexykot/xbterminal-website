# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-10-14 19:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0094_data_currency_dash'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='currency',
            options={'ordering': ('is_fiat', 'id'), 'verbose_name_plural': 'currencies'},
        ),
        migrations.AddField(
            model_name='currency',
            name='is_enabled',
            field=models.BooleanField(default=True),
            preserve_default=False,
        ),
    ]
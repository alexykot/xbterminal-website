# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-10-06 14:43
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0012_data_transaction_coin'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deposit',
            name='coin_type',
        ),
        migrations.RemoveField(
            model_name='withdrawal',
            name='coin_type',
        ),
        migrations.AlterField(
            model_name='deposit',
            name='coin',
            field=models.ForeignKey(help_text='Crypto currency used for transaction processing.', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='website.Currency'),
        ),
        migrations.AlterField(
            model_name='withdrawal',
            name='coin',
            field=models.ForeignKey(help_text='Crypto currency used for transaction processing.', on_delete=django.db.models.deletion.PROTECT, related_name='+', to='website.Currency'),
        ),
    ]

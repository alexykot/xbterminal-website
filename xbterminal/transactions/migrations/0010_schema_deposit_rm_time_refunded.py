# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-07-02 20:52
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0009_data_deposit_refund_coin_amount'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deposit',
            name='time_refunded',
        ),
    ]
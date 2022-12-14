# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-06-17 09:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0090_schema_merchant_tx_confidence'),
        ('wallet', '0003_schema_address'),
        ('transactions', '0002_schema_deposit_time_broadcasted'),
    ]

    operations = [
        migrations.CreateModel(
            name='BalanceChange',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=8, max_digits=18)),
                ('account', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='website.Account')),
                ('address', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='wallet.Address')),
                ('deposit', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='transactions.Deposit')),
            ],
        ),
    ]

# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-06-17 12:21
from __future__ import unicode_literals

from django.db import migrations


def create_balance_changes(apps, schema_editor):
    Deposit = apps.get_model('transactions', 'Deposit')
    for deposit in Deposit.objects.all():
        if deposit.time_received and not deposit.time_refunded:
            deposit.balancechange_set.create(
                account=deposit.account,
                address=deposit.deposit_address,
                amount=deposit.paid_coin_amount - deposit.fee_coin_amount)
            if deposit.fee_coin_amount > 0:
                deposit.balancechange_set.create(
                    account=None,
                    address=deposit.deposit_address,
                    amount=deposit.fee_coin_amount)


def delete_balance_changes(apps, schema_editor):
    BalanceChange = apps.get_model('transactions', 'BalanceChanges')
    BalanceChange.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0003_schema_balancechange'),
    ]

    operations = [
        migrations.RunPython(create_balance_changes,
                             delete_balance_changes),
    ]

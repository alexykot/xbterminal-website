# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-10-06 15:58
from __future__ import unicode_literals

from django.db import migrations


def change_accounts(apps, schema_editor):
    Device = apps.get_model('website', 'Device')
    for device in Device.objects.filter(account__isnull=False):
        if device.account.currency.is_fiat:
            device.account = device.merchant.account_set.get(currency__name='BTC')
            device.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0092_data_currency_is_fiat'),
    ]

    operations = [
        migrations.RunPython(change_accounts,
                             migrations.RunPython.noop),
    ]

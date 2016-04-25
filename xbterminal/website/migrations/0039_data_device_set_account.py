# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_accounts(apps, schema_editor):
    Device = apps.get_model('website', 'Device')
    Account = apps.get_model('website', 'Account')
    for device in Device.objects.exclude(status='registered'):
        if device.percent == 0:
            if device.bitcoin_network == 'mainnet':
                device.account = Account.objects.get(
                    merchant=device.merchant,
                    currency__name='BTC')
            else:
                try:
                    device.account = Account.objects.get(
                        merchant=device.merchant,
                        currency__name='TBTC')
                except Account.DoesNotExist:
                    continue
        elif device.percent == 100:
            try:
                device.account = Account.objects.get(
                    merchant=device.merchant,
                    currency=device.merchant.currency)
            except Account.DoesNotExist:
                continue
        else:
            raise AssertionError
        device.save()


def unset_accounts(apps, schema_editor):
    Device = apps.get_model('website', 'Device')
    for device in Device.objects.all():
        device.account = None
        device.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0038_schema_device_account'),
    ]

    operations = [
        migrations.RunPython(set_accounts,
                             unset_accounts),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_account_currency(apps, schema_editor):
    Currency = apps.get_model('website', 'Currency')
    Account = apps.get_model('website', 'Account')
    btc = Currency.objects.get(name='BTC')
    tbtc = Currency.objects.get(name='TBTC')
    for account in Account.objects.all():
        if account.network == 'mainnet':
            account.currency = btc
        elif account.network == 'testnet':
            account.currency = tbtc
        account.save()


def unset_account_currency(apps, schema_editor):
    Account = apps.get_model('website', 'Account')
    for account in Account.objects.all():
        account.currency = None
        account.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0028_schema_account_currency'),
    ]

    operations = [
        migrations.RunPython(set_account_currency,
                             unset_account_currency),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def create_btc_accounts(apps, schema_editor):
    Currency = apps.get_model('website', 'Currency')
    MerchantAccount = apps.get_model('website', 'MerchantAccount')
    Account = apps.get_model('website', 'Account')
    btc = Currency.objects.get(name='BTC')
    for merchant in MerchantAccount.objects.all():
        Account.objects.create(merchant=merchant, currency=btc)
    


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0030_schema_account_rm_network'),
    ]

    operations = [
        migrations.RunPython(create_btc_accounts,
                             reverse_code=lambda a, s: None),
    ]

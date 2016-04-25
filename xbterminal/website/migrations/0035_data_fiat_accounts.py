# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def create_fiat_accounts(apps, schema_editor):
    MerchantAccount = apps.get_model('website', 'MerchantAccount')
    Account = apps.get_model('website', 'Account')
    for merchant in MerchantAccount.objects.all():
        if merchant.payment_processor == 'cryptopay' and merchant.api_key:
            Account.objects.create(
                merchant=merchant,
                currency=merchant.currency,
                instantfiat_provider=1,
                instantfiat_api_key=merchant.api_key)


def remove_fiat_accounts(apps, schema_editor):
    Account = apps.get_model('website', 'Account')
    Account.objects.exclude(currency__name__in=['BTC', 'TBTC']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0034_schema_account_instantfiat'),
    ]

    operations = [
        migrations.RunPython(create_fiat_accounts,
                             remove_fiat_accounts),
    ]

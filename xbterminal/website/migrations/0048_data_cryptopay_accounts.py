# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from website.models import INSTANTFIAT_PROVIDERS


def create_accounts(apps, schema_editor):
    Currency = apps.get_model('website', 'Currency')
    MerchantAccount = apps.get_model('website', 'MerchantAccount')
    for merchant in MerchantAccount.objects.all():
        managed_account = merchant.account_set.filter(
            instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
            instantfiat_merchant_id__isnull=False).first()
        if managed_account:
            for currency in Currency.objects.filter(name__in=['GBP', 'USD', 'EUR']):
                if merchant.account_set.filter(currency=currency).exists():
                    continue
                merchant.account_set.create(
                    currency=currency,
                    instantfiat_provider=INSTANTFIAT_PROVIDERS.CRYPTOPAY,
                    instantfiat_merchant_id=managed_account.instantfiat_merchant_id,
                    instantfiat_api_key=managed_account.instantfiat_api_key)


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0047_data_account_forward_address'),
    ]

    operations = [
        migrations.RunPython(create_accounts,
                             migrations.RunPython.noop),
    ]

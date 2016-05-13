# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def copy_instantfiat_settings(apps, schema_editor):
    MerchantAccount = apps.get_model('website', 'MerchantAccount')
    for merchant in MerchantAccount.objects.all():
        settings = set()
        for account in merchant.account_set.exclude(
                currency__name__in=['BTC', 'TBTC']):
            settings.add((
                account.instantfiat_provider,
                account.instantfiat_merchant_id,
                account.instantfiat_api_key))
        assert len(settings) <= 1
        if len(settings) == 0:
            continue
        (merchant.instantfiat_provider,
         merchant.instantfiat_merchant_id,
         merchant.instantfiat_api_key) = settings.pop()
        merchant.save()


def clear_instantfiat_settings(apps, schema_editor):
    MerchantAccount = apps.get_model('website', 'MerchantAccount')
    for merchant in MerchantAccount.objects.all():
        merchant.instantfiat_provider = None
        merchant.instantfiat_merchant_id = None
        merchant.instantfiat_api_key = None
        merchant.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0049_schema_merchant_ift_fields'),
    ]

    operations = [
        migrations.RunPython(copy_instantfiat_settings,
                             clear_instantfiat_settings),
    ]

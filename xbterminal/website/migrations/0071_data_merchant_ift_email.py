# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_instantfiat_email(apps, schema_editor):
    MerchantAccount = apps.get_model('website', 'MerchantAccount')
    for merchant in MerchantAccount.objects.all():
        if merchant.instantfiat_api_key:
            merchant.instantfiat_email = merchant.user.email
            merchant.save()


def unset_instantfiat_email(apps, schema_editor):
    MerchantAccount = apps.get_model('website', 'MerchantAccount')
    for merchant in MerchantAccount.objects.all():
        merchant.instantfiat_email = None
        merchant.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0070_schema_merchant_ift_email'),
    ]

    operations = [
        migrations.RunPython(set_instantfiat_email,
                             unset_instantfiat_email),
    ]

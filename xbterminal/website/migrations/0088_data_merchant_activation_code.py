# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-05-09 11:52
from __future__ import unicode_literals

from django.db import migrations
from website.models import generate_alphanumeric_code


def set_activation_code(apps, schema_editor):
    MerchantAccount = apps.get_model('website', 'MerchantAccount')
    for merchant in MerchantAccount.objects.all():
        merchant.activation_code = generate_alphanumeric_code()
        merchant.save()


def unset_activation_code(apps, schema_editor):
    MerchantAccount = apps.get_model('website', 'MerchantAccount')
    for merchant in MerchantAccount.objects.all():
        merchant.activation_code = None
        merchant.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0087_schema_merchant_activation_code'),
    ]

    operations = [
        migrations.RunPython(set_activation_code,
                             unset_activation_code),
    ]

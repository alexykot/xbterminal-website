# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def create_addresses(apps, schema_editor):
    Account = apps.get_model('website', 'Account')
    Address = apps.get_model('website', 'Address')
    for account in Account.objects.all():
        if account.bitcoin_address:
            Address.objects.create(account=account,
                                   address=account.bitcoin_address)


def remove_addresses(apps, schema_editor):
    Address = apps.get_model('website', 'Address')
    Address.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0059_schema_address'),
    ]

    operations = [
        migrations.RunPython(create_addresses, remove_addresses),
    ]

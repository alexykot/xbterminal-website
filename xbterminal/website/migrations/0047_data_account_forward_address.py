# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_forward_address(apps, schema_editor):
    Account = apps.get_model('website', 'Account')
    for account in Account.objects.filter(currency__name__in=['BTC', 'TBTC']):
        device = account.device_set.\
            filter(bitcoin_address__isnull=False).\
            order_by('-last_activity').first()
        if device:
            account.forward_address = device.bitcoin_address
            account.save()


def unset_forward_address(apps, schema_editor):
    Account = apps.get_model('website', 'Account')
    for account in Account.objects.filter(currency__name__in=['BTC', 'TBTC']):
        account.forward_address = None
        account.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0046_schema_account_forward_address'),
    ]

    operations = [
        migrations.RunPython(set_forward_address,
                             unset_forward_address),
    ]

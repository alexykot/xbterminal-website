# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_max_payout(apps, schema_editor):
    Account = apps.get_model('website', 'Account')
    for account in Account.objects.filter(instantfiat=False):
        account.max_payout = account.balance_max / 3
        account.save()


def unset_max_payout(apps, schema_editor):
    Account = apps.get_model('website', 'Account')
    for account in Account.objects.all():
        account.max_payout = 0
        account.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0062_schema_account_max_payout'),
    ]

    operations = [
        migrations.RunPython(set_max_payout, unset_max_payout),
    ]

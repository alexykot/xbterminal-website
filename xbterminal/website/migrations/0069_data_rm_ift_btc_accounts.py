# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def remove_accounts(apps, schema_editor):
    Account = apps.get_model('website', 'Account')
    for account in Account.objects.filter(instantfiat=True,
                                          currency__name='BTC'):
        account.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0068_schema_rm_recon_time'),
    ]

    operations = [
        migrations.RunPython(remove_accounts, migrations.RunPython.noop),
    ]

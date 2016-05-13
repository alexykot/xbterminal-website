# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_instantfiat_flag(apps, schema_editor):
    Account = apps.get_model('website', 'Account')
    for account in Account.objects.all():
        account.instantfiat = (account.instantfiat_provider is not None)
        account.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0051_schema_account_ift_id'),
    ]

    operations = [
        migrations.RunPython(set_instantfiat_flag,
                             migrations.RunPython.noop),
    ]

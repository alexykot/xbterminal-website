# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def create_transactions(apps, schema_editor):
    Account = apps.get_model('website', 'Account')
    Transaction = apps.get_model('website', 'Transaction')
    for account in Account.objects.all():
        Transaction.objects.create(account=account,
                                   amount=account.balance)


def remove_transactions(apps, schema_editor):
    Transaction = apps.get_model('website', 'Transaction')
    Transaction.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0042_schema_transaction'),
    ]

    operations = [
        migrations.RunPython(create_transactions,
                             remove_transactions),
    ]

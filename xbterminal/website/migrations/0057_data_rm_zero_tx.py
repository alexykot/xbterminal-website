# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def remove_zero_tx(apps, schema_editor):
    Transaction = apps.get_model('website', 'Transaction')
    for transaction in Transaction.objects.all():
        if not transaction.amount:
            if hasattr(transaction, 'paymentorder'):
                transaction.paymentorder.account_tx = None
                transaction.paymentorder.save()
            elif hasattr(transaction, 'withdrawalorder'):
                transaction.withdrawalorder.account_tx = None
                transaction.withdrawalorder.save()
            transaction.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0056_schema_document_types'),
    ]

    operations = [
        migrations.RunPython(remove_zero_tx,
                             migrations.RunPython.noop),
    ]

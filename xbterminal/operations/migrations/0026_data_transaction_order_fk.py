# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_transaction_order(apps, schema_editor):
    PaymentOrder = apps.get_model('operations', 'PaymentOrder')
    WithdrawalOrder = apps.get_model('operations', 'WithdrawalOrder')
    for order in PaymentOrder.objects.all():
        if order.account_tx:
            order.account_tx.payment = order
            order.account_tx.save()
    for order in WithdrawalOrder.objects.all():
        if order.account_tx:
            order.account_tx.withdrawal = order
            order.account_tx.save()


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0025_schema_rm_order'),
        ('website', '0058_schema_transaction_order_fk'),
    ]

    operations = [
        migrations.RunPython(set_transaction_order,
                             migrations.RunPython.noop),
    ]

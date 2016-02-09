# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def copy_incoming_tx_id(apps, schema_editor):
    PaymentOrder = apps.get_model('operations', 'PaymentOrder')
    for order in PaymentOrder.objects.all():
        if order.incoming_tx_id is not None:
            order.incoming_tx_ids = [order.incoming_tx_id]
            order.save()


def erase_incoming_tx_ids(apps, schema_editor):
    PaymentOrder = apps.get_model('operations', 'PaymentOrder')
    for order in PaymentOrder.objects.all():
        order.incoming_tx_ids = [order.incoming_tx_id]
        order.save()


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0018_schema_po_add_incoming_tx_ids'),
    ]

    operations = [
        migrations.RunPython(copy_incoming_tx_id,
                             erase_incoming_tx_ids),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def set_bitcoin_network(apps, schema_editor):
    PaymentOrder = apps.get_model('operations', 'PaymentOrder')
    for order in PaymentOrder.objects.all():
        if order.local_address.startswith('1'):
            order.bitcoin_network = 'mainnet'
        elif order.local_address.startswith('m') or \
                order.local_address.startswith('n'):
            order.bitcoin_network = 'testnet'
        else:
            raise ValueError
        order.save()


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0009_schema_po_bitcoin_network'),
    ]

    operations = [
        migrations.RunPython(set_bitcoin_network,
                             reverse_code=lambda a, s: None),
    ]

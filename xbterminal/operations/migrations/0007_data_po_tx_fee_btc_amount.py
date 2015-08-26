# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def calculate_tx_fee(apps, schema_editor):
    PaymentOrder = apps.get_model('operations', 'PaymentOrder')
    for order in PaymentOrder.objects.all():
        order.tx_fee_btc_amount = (order.btc_amount -
                                   order.merchant_btc_amount -
                                   order.instantfiat_btc_amount -
                                   order.fee_btc_amount)
        order.save()


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0006_schema_po_tx_fee_btc_amount'),
    ]

    operations = [
        migrations.RunPython(calculate_tx_fee,
                             reverse_code=lambda a, s: None),
    ]

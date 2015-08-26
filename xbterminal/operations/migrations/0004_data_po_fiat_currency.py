# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def set_currency(apps, schema_editor):
    PaymentOrder = apps.get_model('operations', 'PaymentOrder')
    Currency = apps.get_model('website', 'Currency')
    for order in PaymentOrder.objects.all():
        currency = Currency.objects.get(name=order.fiat_currency)
        order.fiat_currency_temp = currency
        order.save()


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0003_schema_po_fiat_currency_temp'),
    ]

    operations = [
        migrations.RunPython(set_currency,
                             reverse_code=lambda a, s: None),
    ]

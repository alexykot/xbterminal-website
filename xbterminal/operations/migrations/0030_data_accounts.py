# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_account(apps, schema_editor):
    PaymentOrder = apps.get_model('operations', 'PaymentOrder')
    WithdrawalOrder = apps.get_model('operations', 'WithdrawalOrder')
    for order in PaymentOrder.objects.all():
        order.account = order.device.account
        order.save()
    for order in WithdrawalOrder.objects.all():
        order.account = order.device.account
        order.save()


def unset_account(apps, schema_editor):
    PaymentOrder = apps.get_model('operations', 'PaymentOrder')
    WithdrawalOrder = apps.get_model('operations', 'WithdrawalOrder')
    for order in PaymentOrder.objects.all():
        order.account = None
        order.save()
    for order in WithdrawalOrder.objects.all():
        order.account = None
        order.save()


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0029_schema_account_field'),
    ]

    operations = [
        migrations.RunPython(set_account, unset_account),
    ]

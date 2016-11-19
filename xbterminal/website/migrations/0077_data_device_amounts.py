# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def set_device_amounts(apps, schema_editor):
    Device = apps.get_model('website', 'Device')
    for device in Device.objects.filter(account__isnull=False):
        device.amount_1 = device.account.currency.amount_1
        device.amount_2 = device.account.currency.amount_2
        device.amount_3 = device.account.currency.amount_3
        device.amount_shift = device.account.currency.amount_shift
        device.save()

def unset_device_amounts(apps, schema_editor):
    Device = apps.get_model('website', 'Device')
    for device in Device.objects.all():
        device.amount_1 = None
        device.amount_2 = None
        device.amount_3 = None
        device.amount_shift = None
        device.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0076_schema_device_amounts'),
    ]

    operations = [
        migrations.RunPython(set_device_amounts,
                             unset_device_amounts),
    ]

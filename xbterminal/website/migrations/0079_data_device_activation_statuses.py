# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def update_device_statuses(apps, schema_editor):
    Device = apps.get_model('website', 'Device')
    for device in Device.objects.filter(status='activation'):
        device.__dict__['status'] = 'activation_error'
        device.save()


def revert_device_statuses(apps, schema_editor):
    Device = apps.get_model('website', 'Device')
    for device in Device.objects.filter(status__startswith='activation'):
        device.__dict__['status'] = 'activation'
        device.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0078_schema_device_activation_statuses'),
    ]

    operations = [
        migrations.RunPython(update_device_statuses,
                             revert_device_statuses),
    ]

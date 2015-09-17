# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def update_statuses(apps, schema_editor):
    Device = apps.get_model('website', 'Device')
    for device in Device.objects.all():
        if device.status in ['suspended', 'disposed']:
            device.status = 'suspended'
        else:
            device.status = 'active'
        device.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0010_schema_increase_device_key_length'),
    ]

    operations = [
        migrations.RunPython(update_statuses,
                             reverse_code=lambda a, s: None),
    ]

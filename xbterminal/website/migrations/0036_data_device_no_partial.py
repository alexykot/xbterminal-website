# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def update_devices(apps, schema_editor):
    Device = apps.get_model('website', 'Device')
    for device in Device.objects.all():
        if 0 < device.percent < 100:
            device.percent = 0
            device.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0035_data_fiat_accounts'),
    ]

    operations = [
        migrations.RunPython(update_devices,
                             reverse_code=lambda a, s: None),
    ]

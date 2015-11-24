# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def set_registered_status(apps, schema_editor):
    Device = apps.get_model('website', 'Device')
    for device in Device.objects.all():
        if device.status == 'activation':
            device.__dict__['status'] = 'registered'
            device.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0020_schema_default_theme'),
    ]

    operations = [
        migrations.RunPython(set_registered_status,
                             reverse_code=lambda a, s: None),
    ]

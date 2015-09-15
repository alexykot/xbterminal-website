# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random
from django.db import models, migrations


def set_activation_codes(apps, schema_editor):
    Device = apps.get_model('website', 'Device')
    chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZ'
    for device in Device.objects.all():
        device.activation_code = ''.join(random.sample(chars, 6))
        device.created_at = device.merchant.user.date_joined
        device.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0015_schema_device_activation_code'),
    ]

    operations = [
        migrations.RunPython(set_activation_codes,
                             reverse_code=lambda a, s: None),
    ]

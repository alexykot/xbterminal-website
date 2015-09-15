# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0011_data_device_statuses'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='status',
            field=django_fsm.FSMField(default=b'activation', protected=True, max_length=50, choices=[(b'activation', 'Activation pending'), (b'active', 'Operational'), (b'suspended', 'Suspended')]),
            preserve_default=True,
        ),
    ]

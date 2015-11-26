# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0021_data_device_statuses'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='status',
            field=django_fsm.FSMField(default=b'registered', protected=True, max_length=50, choices=[(b'registered', 'Registered'), (b'activation', 'Activation in progress'), (b'active', 'Operational'), (b'suspended', 'Suspended')]),
            preserve_default=True,
        ),
    ]

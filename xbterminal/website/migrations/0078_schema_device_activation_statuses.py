# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0077_data_device_amounts'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='status',
            field=django_fsm.FSMField(default=b'registered', protected=True, max_length=50, choices=[(b'registered', 'Registered'), (b'activation_in_progress', 'Activation in progress'), (b'activation_error', 'Activation error'), (b'active', 'Operational'), (b'suspended', 'Suspended')]),
        ),
    ]

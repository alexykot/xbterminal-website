# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from website.fixtures.groups import update_groups


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0079_data_device_activation_statuses'),
    ]

    operations = [
        migrations.RunPython(update_groups,
                             migrations.RunPython.noop),
    ]

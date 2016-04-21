# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0039_data_device_set_account'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='device',
            name='bitcoin_network',
        ),
    ]

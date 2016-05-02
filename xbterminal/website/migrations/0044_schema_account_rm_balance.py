# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0043_data_create_transactions'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='balance',
        ),
    ]

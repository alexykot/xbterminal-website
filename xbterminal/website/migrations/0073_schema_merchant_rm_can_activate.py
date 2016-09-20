# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0072_schema_account_upd_uniq'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='merchantaccount',
            name='can_activate_device',
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0032_schema_account_unique'),
    ]

    operations = [
        migrations.RenameField(
            model_name='account',
            old_name='address',
            new_name='bitcoin_address',
        ),
    ]

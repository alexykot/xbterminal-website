# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0024_schema_account_tx'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='merchant',
        ),
        migrations.DeleteModel(
            name='Order',
        ),
    ]

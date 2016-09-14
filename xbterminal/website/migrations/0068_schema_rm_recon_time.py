# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0067_schema_merchant_validate_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reconciliationtime',
            name='device',
        ),
        migrations.RemoveField(
            model_name='device',
            name='last_reconciliation',
        ),
        migrations.DeleteModel(
            name='ReconciliationTime',
        ),
    ]

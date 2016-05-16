# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0053_schema_transaction_ift_tx_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='merchantaccount',
            name='can_activate_device',
            field=models.BooleanField(default=False),
        ),
    ]

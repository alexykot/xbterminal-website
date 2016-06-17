# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0063_data_account_max_payout'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='balance_max',
        ),
    ]

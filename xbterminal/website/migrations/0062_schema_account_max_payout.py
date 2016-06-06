# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0061_schema_account_rm_bitcoin_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='max_payout',
            field=models.DecimalField(default=0, verbose_name='Maximum payout', max_digits=20, decimal_places=8),
        ),
    ]

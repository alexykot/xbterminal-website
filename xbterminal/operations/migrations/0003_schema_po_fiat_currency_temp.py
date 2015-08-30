# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0003_schema_move_models'),
        ('operations', '0002_schema_po_time_created_now'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentorder',
            name='fiat_currency_temp',
            field=models.ForeignKey(to='website.Currency', null=True),
            preserve_default=True,
        ),
    ]

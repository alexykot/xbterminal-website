# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0042_schema_transaction'),
        ('operations', '0023_schema_po_rm_btc_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentorder',
            name='account_tx',
            field=models.OneToOneField(null=True, to='website.Transaction'),
        ),
        migrations.AddField(
            model_name='withdrawalorder',
            name='account_tx',
            field=models.OneToOneField(null=True, to='website.Transaction'),
        ),
    ]

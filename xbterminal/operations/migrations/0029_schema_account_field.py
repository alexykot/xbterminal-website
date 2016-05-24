# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0058_schema_transaction_order_fk'),
        ('operations', '0028_schema_wo_instantfiat_transfer'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentorder',
            name='account',
            field=models.ForeignKey(to='website.Account', null=True),
        ),
        migrations.AddField(
            model_name='withdrawalorder',
            name='account',
            field=models.ForeignKey(to='website.Account', null=True),
        ),
    ]

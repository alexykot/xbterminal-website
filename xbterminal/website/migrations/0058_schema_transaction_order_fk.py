# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0025_schema_rm_order'),
        ('website', '0057_data_rm_zero_tx'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='payment',
            field=models.ForeignKey(blank=True, to='operations.PaymentOrder', null=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='withdrawal',
            field=models.ForeignKey(blank=True, to='operations.WithdrawalOrder', null=True),
        ),
    ]

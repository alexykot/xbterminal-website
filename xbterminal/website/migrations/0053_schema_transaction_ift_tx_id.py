# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0052_data_account_instantfiat'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='instantfiat_tx_id',
            field=models.CharField(max_length=64, null=True, verbose_name='InstantFiat transaction ID', blank=True),
        ),
        migrations.AlterUniqueTogether(
            name='transaction',
            unique_together=set([('account', 'instantfiat_tx_id')]),
        ),
    ]

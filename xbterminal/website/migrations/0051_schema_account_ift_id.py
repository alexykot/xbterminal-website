# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0050_data_fill_merchant_ift_fields'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='account',
            options={'ordering': ('merchant', 'instantfiat', 'currency')},
        ),
        migrations.AddField(
            model_name='account',
            name='instantfiat',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='instantfiat_account_id',
            field=models.CharField(max_length=50, unique=True, null=True, verbose_name='InstantFiat account ID', blank=True),
        ),
        migrations.AlterUniqueTogether(
            name='account',
            unique_together=set([('merchant', 'instantfiat', 'currency')]),
        ),
    ]

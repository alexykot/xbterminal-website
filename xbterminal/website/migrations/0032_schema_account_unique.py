# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import website.validators


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0031_data_create_btc_accounts'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='account',
            options={'ordering': ('merchant', 'currency')},
        ),
        migrations.AlterField(
            model_name='account',
            name='address',
            field=models.CharField(blank=True, max_length=35, unique=True, null=True, validators=[website.validators.validate_bitcoin_address]),
        ),
        migrations.AlterUniqueTogether(
            name='account',
            unique_together=set([('merchant', 'currency')]),
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import website.validators


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0045_schema_account_ift_merchant_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='forward_address',
            field=models.CharField(blank=True, max_length=35, null=True, validators=[website.validators.validate_bitcoin_address]),
        ),
    ]

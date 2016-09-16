# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0069_data_rm_ift_btc_accounts'),
    ]

    operations = [
        migrations.AddField(
            model_name='merchantaccount',
            name='instantfiat_email',
            field=models.EmailField(max_length=254, null=True, verbose_name='InstantFiat merchant email', blank=True),
        ),
    ]

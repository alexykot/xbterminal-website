# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0027_data_currency_btc'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='currency',
            field=models.ForeignKey(to='website.Currency', null=True),
        ),
    ]

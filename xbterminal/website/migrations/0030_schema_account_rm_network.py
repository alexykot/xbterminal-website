# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0029_data_account_currency'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='network',
        ),
        migrations.AlterField(
            model_name='account',
            name='currency',
            field=models.ForeignKey(to='website.Currency'),
        ),
    ]

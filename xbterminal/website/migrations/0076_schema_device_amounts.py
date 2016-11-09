# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0075_schema_currency_amounts'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='amount_1',
            field=models.DecimalField(null=True, max_digits=12, decimal_places=2, blank=True),
        ),
        migrations.AddField(
            model_name='device',
            name='amount_2',
            field=models.DecimalField(null=True, max_digits=12, decimal_places=2, blank=True),
        ),
        migrations.AddField(
            model_name='device',
            name='amount_3',
            field=models.DecimalField(null=True, max_digits=12, decimal_places=2, blank=True),
        ),
        migrations.AddField(
            model_name='device',
            name='amount_shift',
            field=models.DecimalField(null=True, max_digits=12, decimal_places=2, blank=True),
        ),
    ]

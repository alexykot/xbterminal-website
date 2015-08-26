# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0004_data_po_fiat_currency'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymentorder',
            name='fiat_currency',
        ),
        migrations.AlterField(
            model_name='paymentorder',
            name='fiat_currency_temp',
            field=models.ForeignKey(to='website.Currency'),
            preserve_default=True,
        ),
        migrations.RenameField(
            model_name='paymentorder',
            old_name='fiat_currency_temp',
            new_name='fiat_currency',
        ),
    ]

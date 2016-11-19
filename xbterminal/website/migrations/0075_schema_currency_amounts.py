# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0074_schema_account_bank_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='currency',
            name='amount_1',
            field=models.DecimalField(default=Decimal('1.00'), help_text='Default value for payment amount button 1.', max_digits=12, decimal_places=2),
        ),
        migrations.AddField(
            model_name='currency',
            name='amount_2',
            field=models.DecimalField(default=Decimal('2.50'), help_text='Default value for payment amount button 2.', max_digits=12, decimal_places=2),
        ),
        migrations.AddField(
            model_name='currency',
            name='amount_3',
            field=models.DecimalField(default=Decimal('10.00'), help_text='Default value for payment amount button 3.', max_digits=12, decimal_places=2),
        ),
        migrations.AddField(
            model_name='currency',
            name='amount_shift',
            field=models.DecimalField(default=Decimal('0.05'), help_text='Default value for payment amount shift button.', max_digits=12, decimal_places=2),
        ),
    ]

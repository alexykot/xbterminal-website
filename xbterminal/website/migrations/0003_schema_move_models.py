# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0002_data_fixtures'),
    ]

    database_operations = [
        migrations.AlterModelTable('PaymentOrder', 'operations_paymentorder'),
        migrations.AlterModelTable('WithdrawalOrder', 'operations_withdrawalorder'),
        migrations.AlterModelTable('Order', 'operations_order'),
    ]

    state_operations = [
        migrations.DeleteModel('PaymentOrder'),
        migrations.DeleteModel('WithdrawalOrder'),
        migrations.DeleteModel('Order'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=database_operations,
            state_operations=state_operations),
    ]

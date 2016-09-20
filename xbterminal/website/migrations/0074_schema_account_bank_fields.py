# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import localflavor.generic.models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0073_schema_merchant_rm_can_activate'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='bank_account_bic',
            field=localflavor.generic.models.BICField(null=True, verbose_name='Bank account BIC', blank=True),
        ),
        migrations.AddField(
            model_name='account',
            name='bank_account_iban',
            field=localflavor.generic.models.IBANField('Bank account IBAN', None, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='account',
            name='bank_account_name',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import website.utils.files


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0044_schema_account_rm_balance'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='instantfiat_merchant_id',
            field=models.CharField(max_length=50, null=True, verbose_name='InstantFiat merchant ID', blank=True),
        ),
        migrations.AlterField(
            model_name='account',
            name='instantfiat_provider',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='InstantFiat provider', choices=[(1, b'CryptoPay'), (2, b'GoCoin')]),
        ),
        migrations.AlterField(
            model_name='kycdocument',
            name='file',
            field=models.FileField(storage=website.utils.files.VerificationFileStorage(), upload_to=website.utils.files.verification_file_path_gen),
        ),
    ]

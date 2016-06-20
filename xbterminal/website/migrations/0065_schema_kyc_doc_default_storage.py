# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import website.utils.files


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0064_schema_account_rm_balance_max'),
    ]

    operations = [
        migrations.AlterField(
            model_name='kycdocument',
            name='file',
            field=models.FileField(upload_to=website.utils.files.verification_file_path_gen),
        ),
    ]

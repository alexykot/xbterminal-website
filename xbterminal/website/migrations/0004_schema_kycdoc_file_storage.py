# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import website.files


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0003_schema_move_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='kycdocument',
            name='file',
            field=models.FileField(storage=website.files.VerificationFileStorage(), upload_to=website.files.verification_file_path_gen),
            preserve_default=True,
        ),
    ]

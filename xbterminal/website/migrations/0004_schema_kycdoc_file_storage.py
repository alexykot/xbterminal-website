# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import website.utils.files


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0003_schema_move_models'),
    ]

    operations = [
        migrations.AlterField(
            model_name='kycdocument',
            name='file',
            field=models.FileField(storage=website.utils.files.VerificationFileStorage(), upload_to=website.utils.files.verification_file_path_gen),
            preserve_default=True,
        ),
    ]

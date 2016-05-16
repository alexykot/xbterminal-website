# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0055_schema_rm_fields'),
    ]

    operations = [
        migrations.RenameField(
            model_name='kycdocument',
            old_name='gocoin_document_id',
            new_name='instantfiat_document_id',
        ),
        migrations.RenameField(
            model_name='kycdocument',
            old_name='uploaded',
            new_name='uploaded_at',
        ),
        migrations.AlterField(
            model_name='kycdocument',
            name='document_type',
            field=models.PositiveSmallIntegerField(choices=[(1, b'ID document - frontside'), (2, b'Address document'), (3, b'ID document - backside')]),
        ),
    ]

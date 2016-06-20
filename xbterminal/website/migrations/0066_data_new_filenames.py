# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def rename_files(apps, schema_editor):
    KYCDocument = apps.get_model('website', 'KYCDocument')
    for document in KYCDocument.objects.all():
        if not document.file.name.startswith('verification'):
            document.file.name = 'verification/' + document.file.name
            document.save()


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0065_schema_kyc_doc_default_storage'),
    ]

    operations = [
        migrations.RunPython(rename_files, migrations.RunPython.noop),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from website.fixtures.batches import update_batches


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0006_schema_batch_number_uuid'),
    ]

    operations = [
        migrations.RunPython(update_batches,
                             reverse_code=lambda a, s: None),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from website.fixtures.currencies import update_currencies


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0023_schema_device_ordering'),
    ]

    operations = [
        migrations.RunPython(update_currencies,
                             reverse_code=lambda a, s: None),
    ]

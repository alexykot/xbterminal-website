# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from website.fixtures.currencies import update_currencies


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0026_schema_rename_btc_account'),
    ]

    operations = [
        migrations.RunPython(update_currencies,
                             reverse_code=lambda a, s: None),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from website.fixtures.themes import update_themes


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0018_schema_ui_theme'),
    ]

    operations = [
        migrations.RunPython(update_themes,
                             reverse_code=lambda a, s: None),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from website.fixtures.sites import update_sites
from website.fixtures.languages import update_languages
from website.fixtures.currencies import update_currencies


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0001_initial'),
        ('sites', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(update_sites,
                             reverse_code=lambda a, s: None),
        migrations.RunPython(update_languages,
                             reverse_code=lambda a, s: None),
        migrations.RunPython(update_currencies,
                             reverse_code=lambda a, s: None),
    ]

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0019_data_default_theme'),
    ]

    operations = [
        migrations.AlterField(
            model_name='merchantaccount',
            name='ui_theme',
            field=models.ForeignKey(default=1, to='website.UITheme'),
            preserve_default=True,
        ),
    ]

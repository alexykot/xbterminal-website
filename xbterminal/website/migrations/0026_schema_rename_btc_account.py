# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import website.validators


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0025_schema_user_model_dj18'),
    ]

    operations = [
        migrations.RenameModel('BTCAccount', 'Account'),
    ]

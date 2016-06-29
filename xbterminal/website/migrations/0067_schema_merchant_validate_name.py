# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0066_data_new_filenames'),
    ]

    operations = [
        migrations.AlterField(
            model_name='merchantaccount',
            name='contact_first_name',
            field=models.CharField(max_length=255, verbose_name='Contact first name', validators=[django.core.validators.RegexValidator(b'^(?u)[^\\W\\d_]+$', b'Enter a valid name. This value may contain only letters.', code=b'invalid_name')]),
        ),
        migrations.AlterField(
            model_name='merchantaccount',
            name='contact_last_name',
            field=models.CharField(max_length=255, verbose_name='Contact last name', validators=[django.core.validators.RegexValidator(b'^(?u)[^\\W\\d_]+$', b'Enter a valid name. This value may contain only letters.', code=b'invalid_name')]),
        ),
    ]

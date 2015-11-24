# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0017_schema_activation_code_nn'),
    ]

    operations = [
        migrations.CreateModel(
            name='UITheme',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='merchantaccount',
            name='ui_theme',
            field=models.ForeignKey(to='website.UITheme', null=True),
            preserve_default=True,
        ),
    ]

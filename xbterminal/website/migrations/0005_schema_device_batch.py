# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import website.models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0004_schema_kycdoc_file_storage'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceBatch',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_number', models.CharField(default=website.models.gen_batch_number, unique=True, max_length=8, editable=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('size', models.IntegerField()),
                ('comment', models.TextField(blank=True)),
            ],
            options={
                'verbose_name': 'batch',
                'verbose_name_plural': 'device batches',
            },
            bases=(models.Model,),
        ),
    ]

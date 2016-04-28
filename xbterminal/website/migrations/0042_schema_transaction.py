# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0041_schema_device_rm_percent'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(max_digits=20, decimal_places=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(to='website.Account')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]

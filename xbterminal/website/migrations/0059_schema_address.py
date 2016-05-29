# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import website.validators


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0058_schema_transaction_order_fk'),
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.CharField(unique=True, max_length=35, validators=[website.validators.validate_bitcoin_address])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('account', models.ForeignKey(to='website.Account')),
            ],
            options={
                'ordering': ['account'],
                'verbose_name_plural': 'addresses',
            },
        ),
    ]

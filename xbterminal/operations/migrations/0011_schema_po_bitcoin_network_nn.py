# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0010_data_po_bitcoin_network'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentorder',
            name='bitcoin_network',
            field=models.CharField(max_length=10, choices=[(b'mainnet', b'Main'), (b'testnet', b'Testnet')]),
            preserve_default=True,
        ),
    ]

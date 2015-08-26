# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('operations', '0008_schema_po_tx_fee_btc_amount_nn'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentorder',
            name='bitcoin_network',
            field=models.CharField(max_length=10, null=True, choices=[(b'mainnet', b'Main'), (b'testnet', b'Testnet')]),
            preserve_default=True,
        ),
    ]

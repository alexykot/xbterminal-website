# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Device.next_firmware'
        db.delete_column(u'website_device', 'next_firmware_id')

        # Deleting field 'Device.current_firmware'
        db.delete_column(u'website_device', 'current_firmware_id')

        # Deleting field 'Device.last_firmware_update_date'
        db.delete_column(u'website_device', 'last_firmware_update_date')


    def backwards(self, orm):
        # Adding field 'Device.next_firmware'
        db.add_column(u'website_device', 'next_firmware',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='next_to_device_set', null=True, to=orm['website.Firmware'], blank=True),
                      keep_default=False)

        # Adding field 'Device.current_firmware'
        db.add_column(u'website_device', 'current_firmware',
                      self.gf('django.db.models.fields.related.ForeignKey')(related_name='current_for_device_set', null=True, to=orm['website.Firmware'], blank=True),
                      keep_default=False)

        # Adding field 'Device.last_firmware_update_date'
        db.add_column(u'website_device', 'last_firmware_update_date',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'website.btcaccount': {
            'Meta': {'object_name': 'BTCAccount'},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '35', 'null': 'True', 'blank': 'True'}),
            'balance': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8'}),
            'balance_max': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '8'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'merchant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['website.MerchantAccount']"}),
            'network': ('django.db.models.fields.CharField', [], {'default': "'mainnet'", 'max_length': '50'})
        },
        u'website.currency': {
            'Meta': {'object_name': 'Currency'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'postfix': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'prefix': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'})
        },
        u'website.device': {
            'Meta': {'ordering': "['id']", 'object_name': 'Device'},
            'api_key': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'bitcoin_address': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'bitcoin_network': ('django.db.models.fields.CharField', [], {'default': "'mainnet'", 'max_length': '50'}),
            'device_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'default': "u'FuFmtkxC'", 'unique': 'True', 'max_length': '32'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_reconciliation': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'merchant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['website.MerchantAccount']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'our_fee_override': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'percent': ('django.db.models.fields.DecimalField', [], {'default': '100', 'max_digits': '4', 'decimal_places': '1'}),
            'serial_number': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'active'", 'max_length': '50'})
        },
        u'website.firmware': {
            'Meta': {'object_name': 'Firmware'},
            'added': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'filename': ('website.fields.FirmwarePathField', [], {'path': "'/var/firmware'", 'max_length': '100'}),
            'hash': ('django.db.models.fields.CharField', [], {'default': "'9495eb30eb674e03a4f539602df6d542'", 'unique': 'True', 'max_length': '32'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'website.kycdocument': {
            'Meta': {'object_name': 'KYCDocument'},
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'document_type': ('django.db.models.fields.IntegerField', [], {}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'gocoin_document_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'merchant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['website.MerchantAccount']"}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'uploaded'", 'max_length': '50'}),
            'uploaded': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        u'website.language': {
            'Meta': {'object_name': 'Language'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '2'}),
            'fractional_split': ('django.db.models.fields.CharField', [], {'default': "'.'", 'max_length': '1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'thousands_split': ('django.db.models.fields.CharField', [], {'default': "','", 'max_length': '1'})
        },
        u'website.merchantaccount': {
            'Meta': {'object_name': 'MerchantAccount'},
            'api_key': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'business_address': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'business_address1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'business_address2': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'company_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'contact_email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'contact_first_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'contact_last_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'contact_phone': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'country': ('django_countries.fields.CountryField', [], {'default': "'GB'", 'max_length': '2'}),
            'county': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128', 'blank': 'True'}),
            'currency': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': u"orm['website.Currency']"}),
            'gocoin_merchant_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': u"orm['website.Language']"}),
            'payment_processor': ('django.db.models.fields.CharField', [], {'default': "'gocoin'", 'max_length': '50'}),
            'post_code': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'town': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'trading_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'merchant'", 'unique': 'True', 'to': u"orm['website.User']"}),
            'verification_status': ('django.db.models.fields.CharField', [], {'default': "'unverified'", 'max_length': '50'})
        },
        u'website.order': {
            'Meta': {'object_name': 'Order'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'delivery_address': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'delivery_address1': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'delivery_address2': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'delivery_contact_phone': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'delivery_country': ('django_countries.fields.CountryField', [], {'default': "'GB'", 'max_length': '2', 'blank': 'True'}),
            'delivery_county': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'delivery_post_code': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'delivery_town': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'fiat_total_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '8'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instantfiat_address': ('django.db.models.fields.CharField', [], {'max_length': '35', 'null': 'True'}),
            'instantfiat_btc_total_amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '18', 'decimal_places': '8'}),
            'instantfiat_invoice_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'merchant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['website.MerchantAccount']"}),
            'payment_method': ('django.db.models.fields.CharField', [], {'default': "'bitcoin'", 'max_length': '50'}),
            'payment_reference': ('django.db.models.fields.CharField', [], {'default': "u'73XPNZADWY'", 'unique': 'True', 'max_length': '10'}),
            'payment_status': ('django.db.models.fields.CharField', [], {'default': "'unpaid'", 'max_length': '50'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {})
        },
        u'website.paymentorder': {
            'Meta': {'object_name': 'PaymentOrder'},
            'btc_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '8'}),
            'device': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['website.Device']"}),
            'effective_exchange_rate': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '8'}),
            'extra_btc_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '18', 'decimal_places': '8'}),
            'fee_address': ('django.db.models.fields.CharField', [], {'max_length': '35'}),
            'fee_btc_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '8'}),
            'fiat_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '8'}),
            'fiat_currency': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'incoming_tx_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'instantfiat_address': ('django.db.models.fields.CharField', [], {'max_length': '35', 'null': 'True'}),
            'instantfiat_btc_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '8'}),
            'instantfiat_fiat_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'}),
            'instantfiat_invoice_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'local_address': ('django.db.models.fields.CharField', [], {'max_length': '35'}),
            'merchant_address': ('django.db.models.fields.CharField', [], {'max_length': '35'}),
            'merchant_btc_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '8'}),
            'outgoing_tx_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'payment_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'receipt_key': ('django.db.models.fields.CharField', [], {'max_length': '32', 'unique': 'True', 'null': 'True'}),
            'refund_address': ('django.db.models.fields.CharField', [], {'max_length': '35', 'null': 'True'}),
            'request': ('django.db.models.fields.BinaryField', [], {}),
            'time_broadcasted': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'time_created': ('django.db.models.fields.DateTimeField', [], {}),
            'time_exchanged': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'time_finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'time_forwarded': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'time_recieved': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'uid': ('django.db.models.fields.CharField', [], {'default': "u'JGk6kt'", 'unique': 'True', 'max_length': '32'})
        },
        u'website.reconciliationtime': {
            'Meta': {'ordering': "['time']", 'object_name': 'ReconciliationTime'},
            'device': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rectime_set'", 'to': u"orm['website.Device']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'time': ('django.db.models.fields.TimeField', [], {})
        },
        u'website.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"})
        },
        u'website.withdrawalorder': {
            'Meta': {'object_name': 'WithdrawalOrder'},
            'bitcoin_network': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'change_btc_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '8'}),
            'customer_address': ('django.db.models.fields.CharField', [], {'max_length': '35', 'null': 'True'}),
            'customer_btc_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '8'}),
            'device': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['website.Device']"}),
            'exchange_rate': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '8'}),
            'fiat_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '12', 'decimal_places': '2'}),
            'fiat_currency': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['website.Currency']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'merchant_address': ('django.db.models.fields.CharField', [], {'max_length': '35'}),
            'outgoing_tx_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'reserved_outputs': ('django.db.models.fields.BinaryField', [], {}),
            'time_broadcasted': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'time_completed': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'time_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'time_sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'tx_fee_btc_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '8'}),
            'uid': ('django.db.models.fields.CharField', [], {'default': "u'9E7m6U'", 'unique': 'True', 'max_length': '32'})
        }
    }

    complete_apps = ['website']
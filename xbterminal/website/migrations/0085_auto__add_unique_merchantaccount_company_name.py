# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding unique constraint on 'MerchantAccount', fields ['company_name']
        db.create_unique(u'website_merchantaccount', ['company_name'])


    def backwards(self, orm):
        # Removing unique constraint on 'MerchantAccount', fields ['company_name']
        db.delete_unique(u'website_merchantaccount', ['company_name'])


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
        u'website.currency': {
            'Meta': {'object_name': 'Currency'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'postfix': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'prefix': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'})
        },
        u'website.device': {
            'Meta': {'ordering': "['id']", 'object_name': 'Device'},
            'bitcoin_address': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'bitcoin_network': ('django.db.models.fields.CharField', [], {'default': "'mainnet'", 'max_length': '50'}),
            'current_firmware': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'current_for_device_set'", 'null': 'True', 'to': u"orm['website.Firmware']"}),
            'device_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'default': "u'RuYfRKF8'", 'unique': 'True', 'max_length': '32'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_firmware_update_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_reconciliation': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'merchant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['website.MerchantAccount']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'next_firmware': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'next_to_device_set'", 'null': 'True', 'to': u"orm['website.Firmware']"}),
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
            'hash': ('django.db.models.fields.CharField', [], {'default': "'8b087a3b339e474e810ef6b69c518e91'", 'unique': 'True', 'max_length': '32'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
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
            'gocoin_merchant_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': u"orm['website.Language']"}),
            'payment_processor': ('django.db.models.fields.CharField', [], {'default': "'gocoin'", 'max_length': '50'}),
            'post_code': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'town': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'trading_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'merchant'", 'unique': 'True', 'to': u"orm['website.User']"}),
            'verification_file_1': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'verification_file_2': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
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
            'payment_reference': ('django.db.models.fields.CharField', [], {'default': "u'D5RJ5EHP5F'", 'unique': 'True', 'max_length': '10'}),
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
            'transaction': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['website.Transaction']", 'unique': 'True', 'null': 'True'}),
            'uid': ('django.db.models.fields.CharField', [], {'default': "'ef629f015fc44aafa441b603074d0cc6'", 'unique': 'True', 'max_length': '32'})
        },
        u'website.reconciliationtime': {
            'Meta': {'ordering': "['time']", 'object_name': 'ReconciliationTime'},
            'device': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rectime_set'", 'to': u"orm['website.Device']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'time': ('django.db.models.fields.TimeField', [], {})
        },
        u'website.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'bitcoin_transaction_id_1': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'bitcoin_transaction_id_2': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'btc_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '8'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dest_address': ('django.db.models.fields.CharField', [], {'max_length': '35', 'null': 'True', 'blank': 'True'}),
            'device': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['website.Device']"}),
            'effective_exchange_rate': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '8'}),
            'fee_btc_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '18', 'decimal_places': '8', 'blank': 'True'}),
            'fiat_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '8'}),
            'fiat_currency': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            'hop_address': ('django.db.models.fields.CharField', [], {'max_length': '35'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instantfiat_address': ('django.db.models.fields.CharField', [], {'max_length': '35', 'null': 'True', 'blank': 'True'}),
            'instantfiat_btc_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '18', 'decimal_places': '8', 'blank': 'True'}),
            'instantfiat_fiat_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '9', 'decimal_places': '2', 'blank': 'True'}),
            'instantfiat_invoice_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'receipt_key': ('django.db.models.fields.CharField', [], {'default': "'a892109e661e4868b66ef2399f92be4c'", 'unique': 'True', 'max_length': '32'}),
            'time': ('django.db.models.fields.DateTimeField', [], {})
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
        }
    }

    complete_apps = ['website']
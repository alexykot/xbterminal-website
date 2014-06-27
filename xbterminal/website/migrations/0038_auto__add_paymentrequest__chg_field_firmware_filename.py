# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PaymentRequest'
        db.create_table(u'website_paymentrequest', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uid', self.gf('django.db.models.fields.CharField')(default='4e94b6abf3ad4b0a8669c65b78ed944b', unique=True, max_length=32)),
            ('device', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['website.Device'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')()),
            ('expires', self.gf('django.db.models.fields.DateTimeField')()),
            ('local_address', self.gf('django.db.models.fields.CharField')(max_length=35)),
            ('merchant_address', self.gf('django.db.models.fields.CharField')(max_length=35)),
            ('fee_address', self.gf('django.db.models.fields.CharField')(max_length=35)),
            ('instantfiat_address', self.gf('django.db.models.fields.CharField')(max_length=35, null=True)),
            ('fiat_currency', self.gf('django.db.models.fields.CharField')(max_length=3)),
            ('fiat_amount', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=8)),
            ('instantfiat_fiat_amount', self.gf('django.db.models.fields.DecimalField')(max_digits=9, decimal_places=2)),
            ('instantfiat_btc_amount', self.gf('django.db.models.fields.DecimalField')(max_digits=18, decimal_places=8)),
            ('merchant_btc_amount', self.gf('django.db.models.fields.DecimalField')(max_digits=18, decimal_places=8)),
            ('fee_btc_amount', self.gf('django.db.models.fields.DecimalField')(max_digits=18, decimal_places=8)),
            ('btc_amount', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=8)),
            ('effective_exchange_rate', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=8)),
            ('instantfiat_invoice_id', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
            ('transaction', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['website.Transaction'], unique=True, null=True)),
        ))
        db.send_create_signal(u'website', ['PaymentRequest'])


        # Changing field 'Firmware.filename'
        db.alter_column(u'website_firmware', 'filename', self.gf('website.fields.FirmwarePathField')(path='/var/firmware', max_length=100))

    def backwards(self, orm):
        # Deleting model 'PaymentRequest'
        db.delete_table(u'website_paymentrequest')


        # Changing field 'Firmware.filename'
        db.alter_column(u'website_firmware', 'filename', self.gf('django.db.models.fields.FilePathField')(path='/var/firmware', max_length=100))

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
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'postfix': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'}),
            'prefix': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '50'})
        },
        u'website.device': {
            'Meta': {'ordering': "['id']", 'object_name': 'Device'},
            'api_key': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'bitcoin_address': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'bitcoin_network': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'currency': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': u"orm['website.Currency']"}),
            'current_firmware': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'current_for_device_set'", 'null': 'True', 'to': u"orm['website.Firmware']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'default': "'65e30b05ea754d0e90f28f67782e11e5'", 'unique': 'True', 'max_length': '32'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': u"orm['website.Language']"}),
            'last_firmware_update_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'last_reconciliation': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'merchant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['website.MerchantAccount']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'next_firmware': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'next_to_device_set'", 'null': 'True', 'to': u"orm['website.Firmware']"}),
            'our_fee_override': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'payment_processing': ('django.db.models.fields.CharField', [], {'default': "'keep'", 'max_length': '50'}),
            'payment_processor': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True'}),
            'percent': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '4', 'decimal_places': '1', 'blank': 'True'}),
            'serial_number': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        },
        u'website.firmware': {
            'Meta': {'object_name': 'Firmware'},
            'added': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'filename': ('website.fields.FirmwarePathField', [], {'path': "'/var/firmware'", 'max_length': '100'}),
            'hash': ('django.db.models.fields.CharField', [], {'default': "'d310f5f086144176b2330fa7bec89d09'", 'unique': 'True', 'max_length': '32'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'version': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'website.language': {
            'Meta': {'object_name': 'Language'},
            'fractional_split': ('django.db.models.fields.CharField', [], {'default': "'.'", 'max_length': '1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'thousands_split': ('django.db.models.fields.CharField', [], {'default': "','", 'max_length': '1'})
        },
        u'website.merchantaccount': {
            'Meta': {'object_name': 'MerchantAccount'},
            'business_address': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'business_address1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1000', 'blank': 'True'}),
            'business_address2': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1000', 'blank': 'True'}),
            'company_name': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'contact_email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'}),
            'contact_name': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'contact_phone': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'country': ('django_countries.fields.CountryField', [], {'default': "'GB'", 'max_length': '2'}),
            'county': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post_code': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'town': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'merchant'", 'unique': 'True', 'null': 'True', 'to': u"orm['auth.User']"})
        },
        u'website.paymentrequest': {
            'Meta': {'object_name': 'PaymentRequest'},
            'btc_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '8'}),
            'created': ('django.db.models.fields.DateTimeField', [], {}),
            'device': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['website.Device']"}),
            'effective_exchange_rate': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '8'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {}),
            'fee_address': ('django.db.models.fields.CharField', [], {'max_length': '35'}),
            'fee_btc_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '8'}),
            'fiat_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '8'}),
            'fiat_currency': ('django.db.models.fields.CharField', [], {'max_length': '3'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instantfiat_address': ('django.db.models.fields.CharField', [], {'max_length': '35', 'null': 'True'}),
            'instantfiat_btc_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '8'}),
            'instantfiat_fiat_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'}),
            'instantfiat_invoice_id': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'local_address': ('django.db.models.fields.CharField', [], {'max_length': '35'}),
            'merchant_address': ('django.db.models.fields.CharField', [], {'max_length': '35'}),
            'merchant_btc_amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '8'}),
            'transaction': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['website.Transaction']", 'unique': 'True', 'null': 'True'}),
            'uid': ('django.db.models.fields.CharField', [], {'default': "'65959a92979e4001a54b3cbd7ae07cd2'", 'unique': 'True', 'max_length': '32'})
        },
        u'website.reconciliationtime': {
            'Meta': {'ordering': "['time']", 'object_name': 'ReconciliationTime'},
            'device': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'rectime_set'", 'to': u"orm['website.Device']"}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
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
            'receipt_key': ('django.db.models.fields.CharField', [], {'default': "'f6a7e337be804e8c896e969a1994ee23'", 'unique': 'True', 'max_length': '32'}),
            'time': ('django.db.models.fields.DateTimeField', [], {})
        }
    }

    complete_apps = ['website']
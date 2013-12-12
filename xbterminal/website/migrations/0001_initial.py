# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Contact'
        db.create_table('website_contact', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=254)),
            ('add_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('message', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'website', ['Contact'])

        # Adding model 'MerchantAccount'
        db.create_table('website_merch_acc', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('contact_phone', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=254)),
            ('business_name', self.gf('django.db.models.fields.CharField')(max_length=1000)),
            ('add_date', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('is_enabled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('house_name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('house_number', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('street_address', self.gf('django.db.models.fields.CharField')(max_length=1000)),
            ('street_address2', self.gf('django.db.models.fields.CharField')(max_length=1000, blank=True)),
            ('town', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('postcode', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
        ))
        db.send_create_signal(u'website', ['MerchantAccount'])


    def backwards(self, orm):
        # Deleting model 'Contact'
        db.delete_table('website_contact')

        # Deleting model 'MerchantAccount'
        db.delete_table('website_merch_acc')


    models = {
        u'website.contact': {
            'Meta': {'object_name': 'Contact'},
            'add_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '254'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {})
        },
        u'website.merchantaccount': {
            'Meta': {'object_name': 'MerchantAccount', 'db_table': "'website_merch_acc'"},
            'add_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'business_name': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'contact_phone': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '254'}),
            'house_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'house_number': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'postcode': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'street_address': ('django.db.models.fields.CharField', [], {'max_length': '1000'}),
            'street_address2': ('django.db.models.fields.CharField', [], {'max_length': '1000', 'blank': 'True'}),
            'town': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['website']
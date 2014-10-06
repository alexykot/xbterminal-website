# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Post.text'
        db.alter_column(u'blog_post', 'text', self.gf('ckeditor.fields.RichTextField')())

    def backwards(self, orm):

        # Changing field 'Post.text'
        db.alter_column(u'blog_post', 'text', self.gf('django.db.models.fields.TextField')())

    models = {
        u'blog.post': {
            'Meta': {'ordering': "['-pub_date']", 'object_name': 'Post'},
            'heading': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pub_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'text': ('ckeditor.fields.RichTextField', [], {})
        }
    }

    complete_apps = ['blog']
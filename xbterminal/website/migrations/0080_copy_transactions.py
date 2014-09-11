# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from constance import config
import uuid


def get_network(address):
    if address.startswith("m") or address.startswith("n"):
        return "testnet"
    elif address.startswith("1") or address.startswith("3"):
        return "mainnet"


def get_transaction_fee_address(transaction):
    transaction_network = get_network(transaction.dest_address)
    if transaction_network == "testnet":
        fee_address = config.OUR_FEE_TESTNET_ADDRESS
    elif transaction_network == "mainnet":
        fee_address = config.OUR_FEE_MAINNET_ADDRESS
    if (
        transaction.device.our_fee_override
        and get_network(transaction.device.our_fee_override) == transaction_network
    ):
        fee_address = transaction.device.our_fee_override
    return fee_address


class Migration(DataMigration):

    def forwards(self, orm):
        for transaction in orm.Transaction.objects.order_by('id'):
            try:
                payment_order = transaction.paymentorder
            except ObjectDoesNotExist:
                if transaction.pk <= 32:
                    default_fee = Decimal('0.00000000')
                else:
                    default_fee = Decimal('0.00010000')
                merchant_btc_amount = (transaction.btc_amount -
                                       transaction.fee_btc_amount -
                                       transaction.instantfiat_btc_amount -
                                       default_fee)
                if merchant_btc_amount < Decimal('0.00000000'):
                    merchant_btc_amount = Decimal('0.00000000')
                payment_order = orm.PaymentOrder(
                    uid=uuid.uuid4().hex,
                    device=transaction.device,
                    local_address=transaction.hop_address,
                    merchant_address=transaction.dest_address,
                    fee_address=get_transaction_fee_address(transaction),
                    instantfiat_address=transaction.instantfiat_address,
                    fiat_currency=transaction.fiat_currency,
                    fiat_amount=transaction.fiat_amount,
                    instantfiat_fiat_amount=transaction.instantfiat_fiat_amount,
                    instantfiat_btc_amount=transaction.instantfiat_btc_amount,
                    merchant_btc_amount=merchant_btc_amount,
                    fee_btc_amount=transaction.fee_btc_amount,
                    btc_amount=transaction.btc_amount,
                    effective_exchange_rate=transaction.effective_exchange_rate,
                    instantfiat_invoice_id=transaction.instantfiat_invoice_id,
                    incoming_tx_id=transaction.bitcoin_transaction_id_1,
                    outgoing_tx_id=transaction.bitcoin_transaction_id_2,
                    payment_type='bip0021',
                    transaction=transaction,
                    time_created=transaction.time,
                    time_finished=transaction.time)
                payment_order.save()

    def backwards(self, orm):
        pass

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
            'key': ('django.db.models.fields.CharField', [], {'default': "u'3F4zwHjh'", 'unique': 'True', 'max_length': '32'}),
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
            'hash': ('django.db.models.fields.CharField', [], {'default': "'a27ea49d386944738eff0bcaf656180f'", 'unique': 'True', 'max_length': '32'}),
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
            'company_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'contact_email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '254'}),
            'contact_first_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'contact_last_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'contact_phone': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'country': ('django_countries.fields.CountryField', [], {'default': "'GB'", 'max_length': '2'}),
            'county': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128', 'blank': 'True'}),
            'currency': ('django.db.models.fields.related.ForeignKey', [], {'default': '1', 'to': u"orm['website.Currency']"}),
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
            'payment_reference': ('django.db.models.fields.CharField', [], {'default': "u'TYDKWVDC1W'", 'unique': 'True', 'max_length': '10'}),
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
            'refund_address': ('django.db.models.fields.CharField', [], {'max_length': '35', 'null': 'True'}),
            'request': ('django.db.models.fields.BinaryField', [], {}),
            'time_broadcasted': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'time_created': ('django.db.models.fields.DateTimeField', [], {}),
            'time_exchanged': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'time_finished': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'time_forwarded': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'time_recieved': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'transaction': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['website.Transaction']", 'unique': 'True', 'null': 'True'}),
            'uid': ('django.db.models.fields.CharField', [], {'default': "'e42db265e22c4293bb8bad4ced406ec2'", 'unique': 'True', 'max_length': '32'})
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
            'receipt_key': ('django.db.models.fields.CharField', [], {'default': "'0d10bfbe39c3433797aa75065b715484'", 'unique': 'True', 'max_length': '32'}),
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
    symmetrical = True

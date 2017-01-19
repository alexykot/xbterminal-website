import datetime

from mock import patch, Mock
from django.contrib.admin.sites import AdminSite
from django.test import TestCase
from django.utils import timezone

from operations.tests.factories import PaymentOrderFactory
from operations.models import PaymentOrder
from operations.admin import PaymentOrderAdmin


class PaymentOrderAdminTestCase(TestCase):

    def setUp(self):
        self.ma = PaymentOrderAdmin(PaymentOrder, AdminSite())

    def test_form(self):
        order = PaymentOrderFactory.create(
            incoming_tx_ids=['0' * 64, '1' * 64],
            outgoing_tx_id='2' * 64)
        form_cls = self.ma.get_form(Mock(), order)
        data = {}
        for field_name, field in form_cls.base_fields.items():
            data[field_name] = field.prepare_value(
                getattr(order, field_name))
        form = form_cls(data=data)
        self.assertTrue(form.is_valid())
        order_updated = form.save()
        self.assertEqual(order_updated.local_address,
                         order.local_address)
        self.assertEqual(order_updated.incoming_tx_ids,
                         order.incoming_tx_ids)
        self.assertEqual(order_updated.outgoing_tx_id,
                         order.outgoing_tx_id)

    @patch('operations.payment.blockchain.BlockChain')
    def test_check_confirmation(self, bc_cls_mock):
        ma = PaymentOrderAdmin(PaymentOrder, AdminSite())
        ma.message_user = Mock()
        bc_cls_mock.return_value = bc_mock = Mock(**{
            'is_tx_confirmed.return_value': True,
        })
        order_1 = PaymentOrderFactory.create()
        self.assertEqual(order_1.status, 'new')
        order_2 = PaymentOrderFactory.create(
            time_created=timezone.now() - datetime.timedelta(hours=5),
            time_received=timezone.now() - datetime.timedelta(hours=5),
            time_forwarded=timezone.now() - datetime.timedelta(hours=5),
            time_notified=timezone.now() - datetime.timedelta(hours=5))
        self.assertEqual(order_2.status, 'unconfirmed')
        ma.check_confirmation(
            Mock(),
            PaymentOrder.objects.filter(pk__in=[order_1.pk, order_2.pk]))
        self.assertTrue(ma.message_user.called)
        self.assertTrue(bc_mock.is_tx_confirmed.called)
        order_1.refresh_from_db()
        self.assertEqual(order_1.status, 'new')
        order_2.refresh_from_db()
        self.assertEqual(order_2.status, 'confirmed')

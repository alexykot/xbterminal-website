import mock
from django.contrib.admin.sites import AdminSite
from django.test import TestCase

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
        form_cls = self.ma.get_form(mock.Mock(), order)
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

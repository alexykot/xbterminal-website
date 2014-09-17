import datetime
from decimal import Decimal
import rq

from django.utils import timezone
import django_rq
from constance import config

from payment.instantfiat import gocoin
from payment.tasks import run_periodic_task

from website.models import Order
from website.utils import send_invoice


def get_terminal_price():
    return config.TERMINAL_PRICE


def get_exchange_rate():
    """
    Get exchange rate from GoCoin
    Returns:
        exchange rate: Decimal
    """
    result = gocoin.create_invoice(
        config.TERMINAL_PRICE,
        'GBP',
        config.GOCOIN_AUTH_TOKEN,
        config.GOCOIN_MERCHANT_ID)
    exchange_rate = result[1] / Decimal(config.TERMINAL_PRICE)
    return float(exchange_rate)


def create_invoice(order):
    """
    Create invoice at GoCoin
    """
    instantfiat_result = gocoin.create_invoice(
        order.fiat_total_amount,
        'GBP',
        config.GOCOIN_AUTH_TOKEN,
        config.GOCOIN_MERCHANT_ID)
    (order.instantfiat_invoice_id,
     order.instantfiat_btc_total_amount,
     order.instantfiat_address) = instantfiat_result
    order.save()
    run_periodic_task(wait_for_payment, [order.pk])


def wait_for_payment(order_id):
    """
    Asynchronous task
    Accepts:
        order_id: Order id
    """
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        # Order or merchant deleted, cancel job
        django_rq.get_scheduler().cancel(rq.get_current_job())
        return
    if order.created + datetime.timedelta(minutes=20) < timezone.now():
        # Timeout, cancel job
        django_rq.get_scheduler().cancel(rq.get_current_job())
    invoice_paid = gocoin.is_invoice_paid(
        order.instantfiat_invoice_id,
        config.GOCOIN_AUTH_TOKEN,
        config.GOCOIN_MERCHANT_ID)
    if invoice_paid:
        django_rq.get_scheduler().cancel(rq.get_current_job())
        order.payment_status = 'paid'
        order.save()
        send_invoice(order)

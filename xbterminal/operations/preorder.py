import datetime
from decimal import Decimal

from django.utils import timezone
from constance import config

from operations.instantfiat import gocoin
from operations.rq_helpers import run_periodic_task, cancel_current_task

from operations.models import Order
from website.utils import send_invoice

PAYMENT_TIMEOUT = datetime.timedelta(minutes=20)


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
        cancel_current_task()
        return
    if order.created + PAYMENT_TIMEOUT < timezone.now():
        # Timeout, cancel job
        cancel_current_task()
    invoice_paid = gocoin.is_invoice_paid(
        order.instantfiat_invoice_id,
        config.GOCOIN_AUTH_TOKEN,
        config.GOCOIN_MERCHANT_ID)
    if invoice_paid:
        cancel_current_task()
        order.payment_status = 'paid'
        order.save()
        send_invoice(order)

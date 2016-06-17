import os

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.utils.html import format_html

from operations.services import blockcypher
from website.utils.qr import generate_qr_code
from api.utils.urls import get_admin_url

register = template.Library()


@register.filter
def scale(value):
    return value * settings.BITCOIN_SCALE_DIVIZER


@register.filter
def amount(value, currency_name):
    if currency_name in ['BTC', 'TBTC']:
        return '{0:.8f}'.format(float(value))
    elif currency_name == 'mBTC':
        return '{0:.5f}'.format(float(value))
    else:
        return '{0:.2f}'.format(float(value))


@register.filter
def admin_url(obj):
    return get_admin_url(obj, absolute=True)


@register.simple_tag
def qr_from_text(text, size):
    src = generate_qr_code(text, size)
    output = format_html('<img src="{0}" alt="{1}">', src, text)
    return output


@register.simple_tag
def pdf_static(path):
    result = os.path.relpath(
        finders.find(path),
        os.path.join(settings.BASE_DIR, '..'))
    return result


@register.simple_tag
def btc_address_url(address, network):
    return blockcypher.get_address_url(address, network)


@register.simple_tag
def btc_tx_url(tx_id, network):
    return blockcypher.get_tx_url(tx_id, network)

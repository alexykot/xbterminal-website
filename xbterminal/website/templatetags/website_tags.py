from django import template
from django.conf import settings
from django.utils.html import format_html

from website.utils import generate_qr_code

register = template.Library()


@register.filter
def scale(value):
    return value * settings.BITCOIN_SCALE_DIVIZER


@register.filter
def amount(value):
    return '{0:g}'.format(float(value))


@register.simple_tag
def qr_from_text(text, size):
    src = generate_qr_code(text, size)
    output = format_html('<img src="{0}" alt="{1}">', src, text)
    return output

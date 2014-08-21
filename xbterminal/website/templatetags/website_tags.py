from django import template
from django.conf import settings

register = template.Library()


@register.filter
def scale(value):
    return value * settings.BITCOIN_SCALE_DIVIZER


@register.filter
def amount(value):
    return '{0:g}'.format(float(value))

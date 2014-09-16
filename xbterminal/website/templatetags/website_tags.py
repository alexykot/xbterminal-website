import os

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.utils.html import format_html

from website.utils import generate_qr_code

register = template.Library()


@register.filter
def scale(value):
    return value * settings.BITCOIN_SCALE_DIVIZER


@register.filter
def amount(value):
    return '{0:g}'.format(float(value))


@register.filter
def kyc_document(merchant, document_type):
    if merchant.verification_status == 'pending':
        status = 'unverified'
    elif merchant.verification_status == 'verified':
        status = 'verified'
    return merchant.get_kyc_document(int(document_type), status)


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

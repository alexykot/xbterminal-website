import re

from django.contrib.sites.models import Site
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.urlresolvers import reverse
from django.utils import translation
from django.utils.html import format_html


def reverse_no_i18n(*args, **kwargs):
    """
    Returns url without language code
    """
    result = reverse(*args, **kwargs)
    current_language = translation.get_language()
    if current_language:
        return re.sub(r'^/' + current_language, '', result)
    return result


def construct_absolute_url(url_name, args=None, kwargs=None):
    site = Site.objects.get_current()
    url_template = '{protocol}://{domain_name}{path}'
    path = reverse_no_i18n(url_name, args=args, kwargs=kwargs)
    url = url_template.format(
        protocol='https' if site.pk == 1 else 'http',
        domain_name=site.domain,
        path=path)
    return url


def get_absolute_static_url(path):
    url = staticfiles_storage.url(path)
    if url.startswith('http'):
        # Already absolute
        return url
    else:
        site = Site.objects.get_current()
        absolute_url = '{protocol}://{domain_name}{path}'.format(
            protocol='https' if site.pk == 1 else 'http',
            domain_name=site.domain,
            path=url)
        return absolute_url


def get_admin_url(obj, absolute=True):
    url_name = u'admin:{0}_{1}_change'.format(
        obj._meta.app_label, obj._meta.model_name)
    if absolute:
        return construct_absolute_url(url_name, args=[obj.pk])
    else:
        return reverse_no_i18n(url_name, args=[obj.pk])


def get_link_to_object(obj):
    return format_html(u'<a href="{0}">{1}</a>',
                       get_admin_url(obj, absolute=False),
                       str(obj))

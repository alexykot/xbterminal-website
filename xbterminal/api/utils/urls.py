from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.urlresolvers import reverse


def construct_absolute_url(url_name, args=None, kwargs=None):
    site = Site.objects.get_current()
    url_template = '{protocol}://{domain_name}{path}'
    url = url_template.format(
        protocol='https' if site.pk == 1 else 'http',
        domain_name=site.domain,
        path=reverse(url_name, args=args, kwargs=kwargs))
    return url


def get_absolute_static_url(path):
    url = staticfiles_storage.url(path)
    if settings.STATICFILES_STORAGE == \
            'storages.backends.s3boto.S3BotoStorage':
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
        return reverse(url_name, args=[obj.pk])

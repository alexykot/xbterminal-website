from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse


def construct_absolute_url(url_name, args=None, kwargs=None):
    site = Site.objects.get_current()
    url_template = '{protocol}://{domain_name}{path}'
    url = url_template.format(
        protocol='https' if site.pk == 1 else 'http',
        domain_name=site.domain,
        path=reverse(url_name, args=args, kwargs=kwargs))
    return url

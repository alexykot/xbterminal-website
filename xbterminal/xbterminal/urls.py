from django.conf.urls import patterns, include, url
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin

from oauth2_provider.views import TokenView

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^django-rq/', include('django_rq.urls')),
    url(r'^oauth/token/', TokenView.as_view(), name='token'),
    url(r'^ckeditor/', include('ckeditor.urls')),
    url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog', {'packages': ('xbterminal',)}),

    url(r'', include('api.urls', namespace='api')),
    url(r'', include('blog.urls', namespace='blog')),
)

urlpatterns += i18n_patterns('',
    url(r'', include('website.urls', namespace='website')),
)

from django.conf.urls import patterns, url


urlpatterns = patterns('api.views',
    url(r'^devices/(?P<key>.{32})/$', 'device'),
)

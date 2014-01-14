from django.conf.urls import patterns, url

from api.views import CreateTransaction


urlpatterns = patterns('api.views',
    url(r'^devices/(?P<key>.{32})/$', 'device', name='device'),
    url(r'^transactions/create/$', CreateTransaction.as_view())
)

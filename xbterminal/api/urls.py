from django.conf.urls import patterns, url

from api.views import CreateTransaction


urlpatterns = patterns('api.views',
    url(r'^devices/(?P<key>[0-9a-fA-F]{32})/$', 'device', name='device'),
    url(r'^transactions/create/$', CreateTransaction.as_view()),
    url(r'^receipts/(?P<key>[0-9a-fA-F]{32})/$', 'transaction_pdf', name='transaction_pdf'),
    url(r'^device/(?P<key>[0-9a-fA-F]{32})/firmware/$', 'device_firmware', name='device_firmware'),
    url(r'^device/(?P<key>[0-9a-fA-F]{32})/firmware/(?P<firmware_hash>[0-9a-fA-F]{32})/$',
        'firmware',
        name='firmware'),
    url(r'^device/(?P<key>[0-9a-fA-F]{32})/firmware_updated/$', 'firmware_updated', name='firmware_updated'),
)

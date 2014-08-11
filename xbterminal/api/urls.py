from django.conf.urls import patterns, url

from api.views import (
    CreateTransaction,
    PaymentInitView,
    PaymentRequestView,
    PaymentResponseView,
    PaymentCheckView)


urlpatterns = patterns('api.views',
    url(r'^devices/(?P<key>[0-9a-zA-Z]{8,32})/$', 'device', name='device'),
    url(r'^transactions/create/$', CreateTransaction.as_view()),
    url(r'^receipts/(?P<key>[0-9a-fA-F]{32})/$', 'transaction_pdf', name='transaction_pdf'),
    url(r'^device/(?P<key>[0-9a-zA-Z]{8,32})/firmware/$', 'device_firmware', name='device_firmware'),
    url(r'^device/(?P<key>[0-9a-zA-Z]{8,32})/firmware/(?P<firmware_hash>[0-9a-fA-F]{32})/$',
        'firmware',
        name='firmware'),
    url(r'^device/(?P<key>[0-9a-zA-Z]{8,32})/firmware_updated/$', 'firmware_updated', name='firmware_updated'),

    url(r'^payments/init$',
        PaymentInitView.as_view(),
        name='payment_init'),
    url(r'^payments/(?P<payment_uid>[0-9a-fA-F]{32})/request$',
        PaymentRequestView.as_view(),
        name='payment_request'),
    url(r'^payments/(?P<payment_uid>[0-9a-fA-F]{32})/response$',
        PaymentResponseView.as_view(),
        name='payment_response'),
    url(r'^payments/(?P<payment_uid>[0-9a-fA-F]{32})/check$',
        PaymentCheckView.as_view(),
        name='payment_check'),
)

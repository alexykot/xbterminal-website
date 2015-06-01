from django.conf.urls import patterns, include, url
from rest_framework import routers
from api import views

router = routers.DefaultRouter()
router.register('withdrawals',
                views.WithdrawalViewSet,
                base_name='withdrawal')


api_urls = patterns(
    'api.views',
    url(r'^', include(router.urls)),
    url(r'^merchant/$',
        views.MerchantView.as_view(),
        name='merchant'),
    url(r'^devices/$',
        views.DevicesView.as_view(),
        name='devices'),
    url(r'^devices/(?P<key>[0-9a-zA-Z]{8,32})/$', 'device', name='device'),
    url(r'^device/(?P<key>[0-9a-zA-Z]{8,32})/firmware/$', 'device_firmware', name='device_firmware'),
    url(r'^device/(?P<key>[0-9a-zA-Z]{8,32})/firmware/(?P<firmware_hash>[0-9a-fA-F]{32})/$',
        'firmware',
        name='firmware'),
    url(r'^device/(?P<key>[0-9a-zA-Z]{8,32})/firmware_updated/$', 'firmware_updated', name='firmware_updated'),

    url(r'^payments/init$',
        views.PaymentInitView.as_view(),
        name='payment_init'),
    url(r'^payments/(?P<payment_uid>[0-9a-zA-Z]{6,32})/request$',
        views.PaymentRequestView.as_view(),
        name='payment_request'),
    url(r'^payments/(?P<payment_uid>[0-9a-zA-Z]{6,32})/response$',
        views.PaymentResponseView.as_view(),
        name='payment_response'),
    url(r'^payments/(?P<payment_uid>[0-9a-zA-Z]{6,32})/check$',
        views.PaymentCheckView.as_view(),
        name='payment_check'),
    url(r'^receipts/(?P<payment_uid>[0-9a-zA-Z]{6,32})/$',
        views.ReceiptView.as_view(),
        name='receipt'),
)

short_urls = patterns(
    'api.views',
    url(r'^pr/(?P<payment_uid>[0-9a-zA-Z]{6,32})$',
        views.PaymentRequestView.as_view(),
        name='payment_request'),
    url(r'^rc/(?P<payment_uid>[0-9a-zA-Z]{6,32})$',
        views.ReceiptView.as_view(),
        name='receipt'),
)

urlpatterns = patterns(
    '',
    url(r'^api/', include(api_urls)),
    url(r'', include(short_urls, namespace='short')),
)

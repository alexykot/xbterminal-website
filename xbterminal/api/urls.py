from django.conf.urls import include, url
from rest_framework import routers
from api import views_v1, views_v2, renderers


api_v1_urls = [
    url(r'^merchant/?$',
        views_v1.MerchantView.as_view(),
        name='merchant'),
    url(r'^devices/?$',
        views_v1.DevicesView.as_view(),
        name='devices'),
    url(r'^devices/(?P<key>[0-9a-zA-Z]{8,32})/?$',
        views_v1.device,
        name='device'),

    url(r'^payments/init/?$',
        views_v1.PaymentInitView.as_view(),
        name='payment_init'),
    url(r'^payments/(?P<payment_uid>[0-9a-zA-Z]{6,32})/request/?$',
        views_v1.PaymentRequestView.as_view(),
        name='payment_request'),
    url(r'^payments/(?P<payment_uid>[0-9a-zA-Z]{6,32})/response/?$',
        views_v1.PaymentResponseView.as_view(),
        name='payment_response'),
    url(r'^payments/(?P<payment_uid>[0-9a-zA-Z]{6,32})/check/?$',
        views_v1.PaymentCheckView.as_view(),
        name='payment_check'),

    url(r'^receipts/(?P<order_uid>[0-9a-zA-Z]{6,32})/?$',
        views_v1.ReceiptView.as_view(),
        name='receipt'),
]

short_urls = [
    url(r'^pr/(?P<payment_uid>[0-9a-zA-Z]{6,32})/?$',
        views_v1.PaymentRequestView.as_view(),
        name='payment_request'),
    url(r'^rc/(?P<order_uid>[0-9a-zA-Z]{6,32})/?$',
        views_v1.ReceiptView.as_view(),
        name='receipt'),
    url(r'^prc/(?P<uid>[0-9a-zA-Z]{6})/?$',
        views_v2.PaymentViewSet.as_view(
            actions={'get': 'receipt'},
            renderer_classes=[renderers.PDFRenderer]),
        name='payment-receipt'),
    url(r'^wrc/(?P<uid>[0-9a-zA-Z]{6})/?$',
        views_v2.WithdrawalViewSet.as_view(
            actions={'get': 'receipt'},
            renderer_classes=[renderers.PDFRenderer]),
        name='withdrawal-receipt'),
]

api_v2_router = routers.DefaultRouter()
api_v2_router.register('payments',
                       views_v2.PaymentViewSet,
                       base_name='payment')
api_v2_router.register('withdrawals',
                       views_v2.WithdrawalViewSet,
                       base_name='withdrawal')
api_v2_router.register('batches',
                       views_v2.DeviceBatchViewSet,
                       base_name='batch')
api_v2_router.register('devices',
                       views_v2.DeviceViewSet,
                       base_name='device')

api_v2_urls = [
    url(r'^', include(api_v2_router.urls)),
]

urlpatterns = [
    url(r'^api/', include(api_v1_urls)),
    url(r'', include(short_urls, namespace='short')),
    url(r'^api/v2/', include(api_v2_urls, namespace='v2')),
]

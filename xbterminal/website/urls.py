from django.conf.urls import patterns, url


from views import (
    ProfileView,
    DeviceView,
    DeviceList,
    SubscribeNewsView,
    EnterAmountView,
    PaymentInitView,
    PaymentRequestView,
    PaymentResponseView,
    PaymentCheckView,
    PaymentSuccessView)

urlpatterns = patterns('website.views',
    url(r'^$', 'landing', name='landing'),
    url(r'^profiles/$', 'profiles', name='profiles'),
    url(r'^subscribe/$', SubscribeNewsView.as_view(), name='subscribe'),
    url(r'^contact/$', 'contact', name='contact'),
    url(r'^faq/$', 'landing_faq', name='landing_faq'),
    url(r'^merchant/$', 'merchant', name='merchant'),

    url(r'^profile/$', ProfileView.as_view(), name='profile'),
    url(r'^devices/$', DeviceList.as_view(), name='devices'),
    url(r'^device/create/$', DeviceView.as_view(), name='create_device'),
    url(r'^device/(?P<number>\d+)/$', DeviceView.as_view(), name='device'),
    url(r'^device/(?P<number>\d+)/reconciliation/$', 'reconciliation', name='reconciliation'),
    url(r'^device/(?P<number>\d+)/reconciliation_time/(?P<pk>\d+)$',
        'reconciliation_time',
        name='reconciliation_time'),

    url(r'^device/(?P<number>\d+)/transactions/$',
        'transactions',
        name='transactions'),
    url(r'^device/(?P<number>\d+)/transactions/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        'transactions',
        name='dated_transactions'),

    url(r'^device/(?P<number>\d+)/receipts/$',
        'receipts',
        name='receipts'),
    url(r'^device/(?P<number>\d+)/receipts/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        'receipts',
        name='dated_receipts'),
    url(r'^device/(?P<number>\d+)/send_all_to_email/$', 'send_all_to_email', name='send_all_to_email'),

    url(r'^device/(?P<number>\d+)/payment/enter_amount$', EnterAmountView.as_view(), name='enter_amount'),
    url(r'^device/(?P<number>\d+)/payment/init$', PaymentInitView.as_view(), name='payment_init'),
    url(r'^payment/(?P<uid>.+)/request$', PaymentRequestView.as_view(), name='payment_request'),
    url(r'^payment/(?P<uid>.+)/response$', PaymentResponseView.as_view(), name='payment_response'),
    url(r'^payment/(?P<uid>.+)/check$', PaymentCheckView.as_view(), name='payment_check'),
    url(r'^device/(?P<number>\d+)/payment/success$', PaymentSuccessView.as_view(), name='payment_success'),
)

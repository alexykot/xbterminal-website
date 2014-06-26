from django.conf.urls import patterns, url


from views import (
    ProfileView,
    DeviceView,
    DeviceList,
    SubscribeNewsView,
    PaymentView)

urlpatterns = patterns('website.views',
    url(r'^$', 'landing', name='landing'),
    url(r'^profiles/$', 'profiles', name='profiles'),
    url(r'^subscribe/$', SubscribeNewsView.as_view(), name='subscribe'),
    url(r'^contact/$', 'contact', name='contact'),
    url(r'^faq/$', 'landing_faq', name='landing_faq'),
    url(r'^merchant/$', 'merchant', name='merchant'),
    url(r'^profile/$', ProfileView.as_view(), name='profile'),

    url(r'^terminals/$', DeviceList.as_view(), name='devices'),
    url(r'^terminals/add/$', DeviceView.as_view(), name='create_device'),
    url(r'^terminals/(?P<device_key>[0-9a-fA-F]{32})/$', DeviceView.as_view(), name='device'),
    url(r'^terminals/(?P<device_key>[0-9a-fA-F]{32})/recon/$', 'reconciliation', name='reconciliation'),
    url(r'^terminals/(?P<device_key>[0-9a-fA-F]{32})/recon_time/(?P<pk>\d+)$',
        'reconciliation_time',
        name='reconciliation_time'),
    url(r'^terminals/(?P<device_key>[0-9a-fA-F]{32})/transactions/$',
        'transactions',
        name='transactions'),
    url(r'^terminals/(?P<device_key>[0-9a-fA-F]{32})/transactions/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        'transactions',
        name='dated_transactions'),
    url(r'^terminals/(?P<device_key>[0-9a-fA-F]{32})/receipts/$',
        'receipts',
        name='receipts'),
    url(r'^terminals/(?P<device_key>[0-9a-fA-F]{32})/receipts/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        'receipts',
        name='dated_receipts'),
    url(r'^terminals/(?P<device_key>[0-9a-fA-F]{32})/send_all_to_email/$',
        'send_all_to_email',
        name='send_all_to_email'),

    url(r'^terminals/(?P<device_key>[0-9a-fA-F]{32})/pos$', PaymentView.as_view(), name='payment'),
)

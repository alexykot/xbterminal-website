from django.conf.urls import patterns, url


from views import ProfileView, DeviceView, DeviceList

urlpatterns = patterns('website.views',
    url(r'^$', 'landing', name='landing'),
    url(r'^contact/$', 'contact', name='contact'),
    url(r'^faq/$', 'landing_faq', name='landing_faq'),
    url(r'^merchant/$', 'merchant', name='merchant'),

    url(r'^profile/$', ProfileView.as_view(), name='profile'),
    url(r'^devices/$', DeviceList.as_view(), name='devices'),
    url(r'^device/create/$', DeviceView.as_view(), name='create_device'),
    url(r'^device/(?P<number>\d+)/$', DeviceView.as_view(), name='device'),
    url(r'^device/(?P<number>\d+)/reconciliation/$', 'reconciliation', name='reconciliation'),

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
    url(r'^device/(?P<number>\d+)/send_all_to_email/$', 'send_all_to_email', name='send_all_to_email')
)

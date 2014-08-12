from django.conf.urls import patterns, url

from website import views
from views import SubscribeNewsView

urlpatterns = patterns('website.views',
    url(r'^$', views.LandingView.as_view(), name='landing'),
    url(r'^privacy/$', views.PrivacyPolicyView.as_view(), name='privacy'),
    url(r'^contact/$', views.ContactView.as_view(), name='contact'),
    url(r'^registration/$', views.RegistrationView.as_view(), name='registration'),
    url(r'^registration/validate/$', views.RegValidationView.as_view(), name='reg_validation'),
    url(r'^order/(?P<pk>\d+)/$', views.OrderPaymentView.as_view(), name='order'),
    url(r'^profiles/$', 'profiles', name='profiles'),
    url(r'^subscribe/$', SubscribeNewsView.as_view(), name='subscribe'),
    url(r'^faq/$', 'landing_faq', name='landing_faq'),
    url(r'^profile/$', views.UpdateProfileView.as_view(), name='profile'),

    url(r'^terminals/$', views.DeviceList.as_view(), name='devices'),
    url(r'^terminals/add/$', views.CreateDeviceView.as_view(), name='create_device'),
    url(r'^terminals/(?P<device_key>[0-9a-zA-Z]{8,32})/$', views.UpdateDeviceView.as_view(), name='device'),
    url(r'^terminals/(?P<device_key>[0-9a-zA-Z]{8,32})/recon/$',
        views.ReconciliationView.as_view(),
        name='reconciliation'),
    url(r'^terminals/(?P<device_key>[0-9a-zA-Z]{8,32})/recon_time/(?P<pk>\d+)$',
        views.ReconciliationTimeView.as_view(),
        name='reconciliation_time'),
    url(r'^terminals/(?P<device_key>[0-9a-zA-Z]{8,32})/transactions/$',
        views.TransactionsView.as_view(),
        name='transactions'),
    url(r'^terminals/(?P<device_key>[0-9a-zA-Z]{8,32})/transactions/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        views.TransactionsView.as_view(),
        name='dated_transactions'),
    url(r'^terminals/(?P<device_key>[0-9a-zA-Z]{8,32})/receipts/$',
        views.ReceiptsView.as_view(),
        name='receipts'),
    url(r'^terminals/(?P<device_key>[0-9a-zA-Z]{8,32})/receipts/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/$',
        views.ReceiptsView.as_view(),
        name='dated_receipts'),
    url(r'^terminals/(?P<device_key>[0-9a-zA-Z]{8,32})/send_all_to_email/$',
        views.SendAllToEmailView.as_view(),
        name='send_all_to_email'),

    url(r'^terminals/(?P<device_key>[0-9a-zA-Z]{8,32})/pos$', views.PaymentView.as_view(), name='payment'),
)

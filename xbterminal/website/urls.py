from django.conf.urls import patterns, url


from views import ProfileView, DeviceView

urlpatterns = patterns('website.views',
    url(r'^$', 'landing', name='landing'),
    url(r'^contact/', 'contact', name='contact'),
    url(r'^faq/', 'landing_faq', name='landing_faq'),
    url(r'^merchant/', 'merchant', name='merchant'),
    url(r'^profile/', ProfileView.as_view(), name='profile'),
    url(r'^device/(?P<number>\d+)/', DeviceView.as_view(), name='device'),
    url(r'^device/create/', DeviceView.as_view(), name='create_device'),
)

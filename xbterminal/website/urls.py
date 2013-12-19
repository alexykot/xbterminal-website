from django.conf.urls import patterns, url

from website import views
from website.forms import AuthenticationForm


urlpatterns = patterns('',
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', {
        'template_name': 'website/login.html',
        'authentication_form': AuthenticationForm
    }),
    url(r'^$', views.landing, name='landing'),
    url(r'^contact/', views.contact, name='contact'),
    url(r'^faq/', views.landing_faq, name='landing_faq'),
    url(r'^merchant/', views.merchant, name='merchant'),
    url(r'^accounts/profile/', views.merchant_cabinet, name='merchant_cabinet'),
)

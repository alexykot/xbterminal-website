from django.conf.urls import patterns, url
from website import views

urlpatterns = patterns('',
  url(r'^$', views.landing, name='landing'),
  url(r'^contact/', views.contact, name='contact'),
  url(r'^faq/',views.landing_faq,name='landing_faq'),
  url(r'^merchant/',views.merchant,name='merchant')
)

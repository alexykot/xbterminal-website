from django.conf.urls import patterns, url
from website import views

urlpatterns = patterns('',
  url(r'^$', views.index, name='index'),
  url(r'^landing/', views.landing, name='landing'),
  url(r'^faq',views.landing_faq,name='landing_faq')
)

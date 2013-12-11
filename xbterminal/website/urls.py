from django.conf.urls import patterns, url
from website import views

urlpatterns = patterns('',
  url(r'^$', views.index, name='index'),
  url(r'^landing/', views.landing, name='landing'),
  url(r'^faq',views.landing_faq,name='landing_faq'),
  url(r'^contact_save',views.contact_form_save,name='contact_save')
)

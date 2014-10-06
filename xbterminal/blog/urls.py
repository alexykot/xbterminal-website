from django.conf.urls import patterns, url

from blog import views

urlpatterns = patterns('website.views',
    url(r'^$', views.IndexView.as_view(), name='posts'),
    url(r'(?P<pk>\d+)/$', views.PostView.as_view(), name='post'),
)

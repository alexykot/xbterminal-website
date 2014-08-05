from django.conf.urls import patterns, include, url
from django.contrib import admin

from website.forms import AuthenticationForm


admin.autodiscover()

urlpatterns = patterns('',
    url(r'^login/$',
        'django.contrib.auth.views.login',
        {
            'template_name': 'cabinet/login.html',
            'authentication_form': AuthenticationForm,
        },
        name='login'),
    url(r'^logout/$',
        'django.contrib.auth.views.logout',
        {'next_page': '/'},
        name='logout'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include('website.urls', namespace='website')),
    url(r'^api/', include('api.urls', namespace='api')),
    url(r'^django-rq/', include('django_rq.urls')),
)

from django.conf.urls import patterns, include, url
from django.contrib import admin

from website.forms import AuthenticationForm


admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'xbterminal.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^login/$', 'django.contrib.auth.views.login', {
            'template_name': 'website/login.html',
            'authentication_form': AuthenticationForm
        },
        'login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}, name='logout'),
    url(r'', include('website.urls', namespace='website')),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^api/', include('api.urls')),
)

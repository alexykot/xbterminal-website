import os
from urlparse import urljoin

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static

from blog import views

blog_urls = patterns('blog.views',
    url(r'^$', views.IndexView.as_view(), name='posts'),
    url(r'(?P<pk>\d+)/$', views.PostView.as_view(), name='post'),
)

urlpatterns = patterns('',
    url(r'^blog/', include(blog_urls)),
)

urlpatterns += static(
    urljoin(settings.MEDIA_URL, 'blog/'),
    document_root=os.path.join(settings.MEDIA_ROOT, 'blog'))

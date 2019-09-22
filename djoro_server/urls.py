from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf.urls import include
from djoro_server import views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'tutorial.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('rest_api.urls')),
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
    url(r'^api-token-auth/', views.djoro_obtain_auth_token),
    url(r'^monitor/', include('monitor.urls')),
    url(r'^dashboard/', include('dashboard.urls')),
)

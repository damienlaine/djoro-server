from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns

from dashboard import views

urlpatterns = [
    url(r'^$', views.index, name='base'),
    url(r'^login/$', views.login_page, name='login_page'),
    url(r'^logout/$', views.logout_view, name='logout_view'),
    url(r'^users/$', views.users, name='users'),
    url(r'^thermostats/(?P<uid>[A-Za-z0-9]+)/*?$', views.thermostat, name='thermostat'),
    url(r'^thermostats/(?P<uid>[A-Za-z0-9]+)/startdate/(?P<startdate_timestamp>[0-9]+)/*?$', views.thermostat, name='thermostat'),
    url(r'^maintenances/$', views.maintenances, name='maintenances')
]

urlpatterns = format_suffix_patterns(urlpatterns)

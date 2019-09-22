from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns

from monitor import views

urlpatterns = [
    url(r'trucverysecret/*?$', views.all, name='all'),
    url(r'thermostats/(?P<uid>[A-Za-z0-9]+)/*?$', views.index, name='index'),
    url(r'thermostats/(?P<uid>[A-Za-z0-9]+)/export_csv/*?$', views.measured_temp_export_csv, name='measured_temp_export_csv'),
]

urlpatterns = format_suffix_patterns(urlpatterns)

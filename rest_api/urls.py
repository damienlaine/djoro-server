from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from rest_api import views

urlpatterns = [
#    url(r'^thermostats/*$', views.ThermostatList.as_view()),
    url(r'^thermostats/my/*$', views.ThermostatDetail.as_view({'get': 'retrieve'})),
    url(r'^thermostats/(?P<pk>[0-9]+)/get_schedule/*?$', views.ThermostatStatus.as_view({'get': 'retrieve'})),
    url(r'^thermostats/(?P<pk>[0-9]+)/history/*$', views.ThermostatHistory.as_view({'get': 'retrieve'})),    
    url(r'^thermostats/(?P<pk>[0-9]+)/markers/*$', views.WeekScheduleMarkerListCreate.as_view({'get': 'get_list', 'post': 'create'})),
    url(r'^thermostats/(?P<pkt>[0-9]+)/markers/(?P<pk>[0-9]+)/*$', views.WeekScheduleMarkerDetail.as_view({'delete': 'delete'})),  
    url(r'^thermostats/(?P<pk>[0-9]+)/special_schedules/*$', views.SpecialScheduleListCreate.as_view({'get': 'get_list', 'post': 'create'})),
    url(r'^thermostats/(?P<pkt>[0-9]+)/special_schedules/(?P<pk>[0-9]+)/*$', views.SpecialScheduleDetail.as_view({'delete': 'delete', 'put': 'put'})),  
    url(r'^thermostats/(?P<pk>[0-9]+)/set_away/*$', views.SpecialScheduleSetAway.as_view({'post': 'create'})),  
    url(r'^thermostats/(?P<pk>[0-9]+)/temperature_modes/*$', views.TemperatureModeListCreate.as_view({'get': 'get_list'})),
    url(r'^thermostats/([0-9]+)/temperature_modes/(?P<pk>[0-9]+)/*$', views.TemperatureModeDetail.as_view({'delete': 'delete'})),
    url(r'^thermostats/(?P<pk>[0-9]+)/saving_proposals/*$', views.SavingProposalList.as_view({'get': 'retrieve'})),
    url(r'^thermostats/(?P<pkt>[0-9]+)/saving_proposals/(?P<pk>[0-9]+)/*$', views.SavingProposalRemoveApply.as_view({'delete': 'delete', 'put': 'apply'})),
#    url(r'^users/*$', views.UserList.as_view()),
#    url(r'^users/(?P<pk>[0-9]+)/*$', views.UserDetail.as_view()),
    url(r'^me/*$', views.UserProfile.as_view({'get': 'get'})),
    url(r'^device/status/*$', views.DeviceStatus.as_view({'post': 'post'})),
]

urlpatterns = format_suffix_patterns(urlpatterns)

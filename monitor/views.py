from django.http import HttpResponse
from django.template import RequestContext, loader

from thermostats.models import Thermostat
from django.shortcuts import get_object_or_404
#from graphos.renderers import gchart

import time
from datetime import datetime, timedelta
import pytz
import json

import logging
logger = logging.getLogger('djoro.monitor')


from django import forms

class DateForm(forms.Form):
    date = forms.DateField(label='Date ')

def index(request, uid=None):

    number_of_days_in_graph = 5
    
    queryset = Thermostat.objects.all()
    thermostat = get_object_or_404(queryset, uid=uid)
    thermostat_timezone = pytz.timezone(thermostat.timezone)

    # Initialize startDate
    startDate = pytz.utc.localize(datetime.now()) - timedelta(days=number_of_days_in_graph)
    # if this is a POST request we retrieve the date from the form
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = DateForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            startDate = form.cleaned_data['date']
            # Add time 00:00 to date
            startDate = datetime.combine(startDate, datetime.min.time())
            # Set to utc            
            startDate = thermostat_timezone.localize(startDate).astimezone(pytz.utc)

    # Set end date
    endDate = startDate + timedelta(days=number_of_days_in_graph)
    
    queryset = thermostat.measuredtemp_set.filter(measuredOn__gte = startDate, measuredOn__lte = endDate).order_by("measuredOn")

    # Prepare data for graph 
    mydata = []
    last_timestamp = 0
    delta_min = 10*60*1000  # Minimum interval in milliseconds between two points on graph
    T_ext = None # T_ext is not recorded in each element. Therefore, we need to keep track of last T_ext recorded.
    for elt in queryset:
        #local_date = elt.measuredOn.astimezone(thermostat_timezone)
        #current_timestamp = time.mktime(local_date.timetuple()) * 1000  # Converts python datetime to javascript timestamp
        if elt.T_ext is not None:
            if elt.T_ext > -50:
                T_ext = elt.T_ext
        utc_date = elt.measuredOn.astimezone(pytz.utc)
        current_timestamp = time.mktime(utc_date.timetuple()) * 1000  # Converts python datetime to javascript timestamp
        # Checks if time between elements is greater than delta_min        
        if (current_timestamp > last_timestamp + delta_min):
            last_timestamp = current_timestamp
            a = current_timestamp
            if elt.temperature > -50:
                b = elt.temperature
            else:
                b = None
            if elt.targetTemperature > -50:
                c = elt.targetTemperature
            else:
                c = None
            if elt.boilerOn:
                d = 25
            else:
                d = 15
            e = elt.userRequestedTemperature
            mydata.append([a,b,c,T_ext, d, e])
    
    # Send data to template
    context = RequestContext(request, {
        'values': json.dumps(mydata),
        'uid': uid,
        'dateForm': DateForm(),
        'number_of_days_in_graph': number_of_days_in_graph
    })
    
    template = loader.get_template('monitor/index.html')
    
    return HttpResponse(template.render(context))

def measured_temp_export_csv(request, uid=None):
    
    queryset = Thermostat.objects.all()
    thermostat = get_object_or_404(queryset, uid=uid)
    
    queryset = thermostat.measuredtemp_set.order_by("measuredOn")

    # Prepare data for export
    mydata = []
    last_timestamp = 0
    delta_min = 3*60*1000  # Minimum interval in milliseconds between two points on graph
    T_ext = "" # T_ext is not recorded in each element. Therefore, we need to keep track of last T_ext recorded.
    for elt in queryset:
        if elt.T_ext is not None:
            if elt.T_ext > -50:
                T_ext = elt.T_ext
        utc_date = elt.measuredOn.astimezone(pytz.utc)
        current_timestamp = time.mktime(utc_date.timetuple()) * 1000  # Converts python datetime to javascript timestamp
        # Checks if time between elements is greater than delta_min        
        if (current_timestamp > last_timestamp + delta_min):
            last_timestamp = current_timestamp
            a = current_timestamp / 1000
            if elt.temperature > -50:
                b = elt.temperature
            else:
                b = ""
            if elt.targetTemperature > -50:
                c = elt.targetTemperature
            else:
                c = ""
            if elt.boilerOn:
                d = "TRUE"
            else:
                d = "FALSE"
            if elt.userRequestedTemperature is not None:
                e = elt.userRequestedTemperature
            else:
                e = ""
            mydata.append({
                'timestamp' : a,
                'Tint' : b,
                'Tcons' : c,
                'Text' : T_ext,
                'boilerOn' : d,
                'userRequestedTemperature': e})
    
    # Send data to template
    context = RequestContext(request, {
        'values': mydata,
        'uid': uid
    })
    
    template = loader.get_template('monitor/measured_temp_export_csv.html')
    
    return HttpResponse(template.render(context))

def all(request):
    
    thermostats = Thermostat.objects.all()
    thermostatsList = []
    for thermostat in thermostats:
        logger.debug('Name: ' + thermostat.name)
        tempTherm = { 'uid': thermostat.uid, 'name': thermostat.name }
        thermostatsList.append(tempTherm)
        
    context = RequestContext(request, {
        'thermostats': thermostatsList,
        'title': "Djoro Thermostats"
    })
    template = loader.get_template('monitor/all.html')
    return HttpResponse(template.render(context))
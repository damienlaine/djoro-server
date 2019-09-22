# -*- coding: utf8 -*-

from django.shortcuts import render

from django.http import HttpResponse
from django.template import RequestContext, loader

from django.contrib.auth import authenticate, login, logout

from thermostats.models import Thermostat, SavingProposal
from dashboard.permissions import is_professional


from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test

from datetime import datetime, timedelta
import pytz
import json
import time

# Create your views here.

import logging
logger = logging.getLogger('djoro.dashboard')

@user_passes_test(is_professional, login_url='/dashboard/login')
def index(request):
    # Send data to template
    #context = RequestContext(request, {
    #    'values': 12,
    #    'uid': 1
    #})
    #template = loader.get_template('dashboard/base.html')
    #return HttpResponse(template.render(context))

    return redirect('/dashboard/users/')

def login_page(request):

    invalid_login_error = False
    disabled_account_error = False

    if request.method == 'POST' and request.POST:
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            # Checks if it is a professional user
            if user.is_active and is_professional(user):
                login(request, user)
                # Retrieve next page to redirect in get parameter, and gives a default value if not provided
                next_page = request.GET.get('next', '/dashboard/')
                return redirect(next_page)
            else:
                # Return a 'disabled account' error message
                disabled_account_error = True
        else:
            # Return an 'invalid login' error message.
            invalid_login_error = True
    
    context = RequestContext(request, {
        'invalid_login_error': invalid_login_error,
        'disabled_account_error': disabled_account_error
    })
    template = loader.get_template('dashboard/login.html')
    return HttpResponse(template.render(context))
    
def logout_view(request):
    logout(request)
    return redirect("/dashboard/login")

@user_passes_test(is_professional, login_url='/dashboard/login')
def users(request):
    number_of_days_for_statistics = 10
    
    # Get professional user thermostats list (or all if user is admin)
    if (request.user.is_superuser):
        thermostats = Thermostat.objects.all()    
    else:
        thermostats = Thermostat.objects.filter(professionalOwner__user__pk = request.user.pk)
    
    thermostatsList = []
    for thermostat in thermostats:
        logger.debug('Name: ' + thermostat.name)
        print(thermostat.professionalOwner)

        # Computes heating speed statistics
        endDate = pytz.utc.localize(datetime.now())
        startDate = endDate - timedelta(days=number_of_days_for_statistics)
        queryset = thermostat.measuredtemp_set.filter(measuredOn__gte = startDate, measuredOn__lte = endDate).order_by("measuredOn")
        statistics = thermostat.stats_heating_speed(queryset)
        if statistics is not None:
            heating_speed_at_7_degrees = statistics['value_at_7_degrees']
            heating_speed_at_0_degrees = statistics['value_at_0_degrees']
            heating_speed_at_all_temperatures = statistics['deriv_value_at_all_temperatures']
            if heating_speed_at_all_temperatures < 0.2:
                heating_speed_issue = 1
            elif ( (heating_speed_at_7_degrees < 0.2) | (heating_speed_at_0_degrees < 0.2)):
                heating_speed_issue = 2
            else:
                heating_speed_issue = 0
        else:
            heating_speed_issue = -1
        
        # Prepare result
        tempTherm = { 
                     'uid': thermostat.uid, 
                     'name': thermostat.name, 
                     'savings': int(thermostat.totalSavingForPeriod),
                     'heating_speed_issue': heating_speed_issue,
                     'minutes_since_last_connection': thermostat.minutes_since_last_connection()
                    }
        thermostatsList.append(tempTherm)
        
    context = RequestContext(request, {
        'thermostats': thermostatsList,
        'title': "Djoro Thermostats",
        'username': request.user.username
    })
    template = loader.get_template('dashboard/users.html')
    return HttpResponse(template.render(context))
    
@user_passes_test(is_professional, login_url='/dashboard/login')
def maintenances(request):
    
    days_validity = 90  # Validity of proposal
    number_of_days_maintenance_old = 270    # Number of days to consider that a maintenance is old

    error_message = ""

    # If POST, it means that we clicked on a button
    if request.method == 'POST':
        # Update last maintenance date        
        if 'update_maintenance_date' in request.POST:
            queryset = Thermostat.objects.filter(professionalOwner__user__pk = request.user.pk)
            thermostat = get_object_or_404(queryset, uid=request.POST.get('uid'))
            print "Date posted = ", request.POST.get('date01')
            try:
                new_date = datetime.strptime(request.POST.get('date01'), '%d/%m/%Y')
                thermostat.last_maintenance_date = new_date
                thermostat.save()
            except:
                error_message = "Vous n'avez pas entré de date valide"    
        
        # Cancel maintenance campaign        
        if 'remove_maintenance_campaign' in request.POST:
            saving_proposal = SavingProposal.objects.get(id=request.POST.get('sp_id'), thermostat__professionalOwner__user__pk = request.user.pk)
            saving_proposal.status = 'CANC'
            saving_proposal.save()

        # Expire maintenance campaign (appointment OK)
        if 'expire_maintenance_campaign' in request.POST:
            saving_proposal = SavingProposal.objects.get(id=request.POST.get('sp_id'), thermostat__professionalOwner__user__pk = request.user.pk)
            saving_proposal.status = 'EXPI'
            saving_proposal.save()

        # New maintenance campaign
        elif 'new_maintenance_campaign' in request.POST or 'new_promo_maintenance_campaign' in request.POST:                
            queryset = Thermostat.objects.filter(professionalOwner__user__pk = request.user.pk)
            thermostat = get_object_or_404(queryset, uid=request.POST.get('uid'))
            # Create saving proposal
            start_validity = datetime.utcnow()
            end_validity = start_validity + timedelta(days=days_validity)
            if 'new_maintenance_campaign' in request.POST:
                title = "Maintenance annuelle de votre chaudière"
                content = "Prenez rendez-vous dès aujourd'hui pour votre maintenance annuelle. C'est obligatoire tous les ans, et c'est important pour votre sécurité."
            if 'new_promo_maintenance_campaign' in request.POST:
                title = "PROMO -10% sur la maintenance de votre chaudière !"
                content = "Prenez rendez-vous dès aujourd'hui pour votre maintenance annuelle. C'est obligatoire tous les ans, et c'est important pour votre sécurité. PROMO -10% sur l'intervention !"
            thermostat.savingproposal_set.create(type='ACTI',
                                                 parameter='maintenance_appointment',
                                                 messageWhenAccepted='Votre entreprise de maintenance va vous contacter pour prendre rendez-vous. Merci !',
                                                 status='PROP',
                                                 startValidityPeriod=start_validity,
                                                 endValidityPeriod=end_validity,
                                                 title=title,
                                                 content=content,
                                                 amount=0)
        


    now = datetime.utcnow()
    
    # Get professional user thermostats list (or all if user is admin)
    if (request.user.is_superuser):
        thermostats = Thermostat.objects.all()    
    else:
        thermostats = Thermostat.objects.filter(professionalOwner__user__pk = request.user.pk)
    
    thermostatsList = []
    for thermostat in thermostats:
        # Checks if maintenance is old
        if (now.date() - thermostat.last_maintenance_date).days > number_of_days_maintenance_old:
            old_maintenance = True
        else:
            old_maintenance = False
        
        campaign_status = ""
        # Checks if we already have a maintenance campaign
        maintenance_proposal = thermostat.savingproposal_set.filter(type='ACTI',
                                                parameter='maintenance_appointment',
                                                startValidityPeriod__lte=now,
                                                endValidityPeriod__gte=now
                                                ).order_by("startValidityPeriod").last()

        campaign_status = ""
        sp_id = ""
        if maintenance_proposal is not None and old_maintenance:
            campaign_status = maintenance_proposal.status
            sp_id = maintenance_proposal.id
        
        # Prepare result
        tempTherm = { 
                     'uid': thermostat.uid, 
                     'name': thermostat.name, 
                     'owner_name' : thermostat.owner.first_name + ' ' + thermostat.owner.last_name,
                     'minutes_since_last_connection': thermostat.minutes_since_last_connection(),
                     'last_maintenance_date': thermostat.last_maintenance_date.strftime("%d/%m/%Y"),
                     'old_maintenance': old_maintenance,
                     'campaign_status': campaign_status,
                     'sp_id': sp_id
                    }
        thermostatsList.append(tempTherm)
       
    context = RequestContext(request, {
        'thermostats': thermostatsList,
        'title': "Djoro Thermostats",
        'error_message': error_message,
        'username': request.user.username
    })
    template = loader.get_template('dashboard/campaigns.html')
    return HttpResponse(template.render(context))
    
                                         
@user_passes_test(is_professional, login_url='/dashboard/login')    
def thermostat(request, uid=None, startdate_timestamp=None):
    
    # Get professional user thermostats list (or all if user is admin)
    if (request.user.is_superuser):
        thermostats = Thermostat.objects.all()    
    else:
        thermostats = Thermostat.objects.filter(professionalOwner__user__pk = request.user.pk)
    thermostat = get_object_or_404(thermostats, uid=uid)
    
    measured_temp = thermostat.get_last_measured_temp().temperature
    
    # Get the schedule without anticipation
    raw_schedule = thermostat.get_raw_schedule()
    userRequestedTemperature = raw_schedule[0].get('temperatureMode').temperature
    if (measured_temp < userRequestedTemperature - 2):
        measured_temp_color = "yellow"
    else:
        measured_temp_color = "green"
    if (thermostat.boilerOn):
        boilerOn = "ON"
        boilerOnColor = "green"
    else:
        boilerOn = "OFF"
        boilerOnColor = "blue"

    #
    # Get measured data
    #

    number_of_days_in_graph = 10

    # Initialize startDate
    if startdate_timestamp is None:
        startDate = pytz.utc.localize(datetime.now()) - timedelta(days=number_of_days_in_graph)
    else:
        startDate = pytz.utc.localize(datetime.fromtimestamp(float(startdate_timestamp)))

    # Set end date
    endDate = startDate + timedelta(days=number_of_days_in_graph)

    # Query measured data   
    queryset = thermostat.measuredtemp_set.filter(measuredOn__gte = startDate, measuredOn__lte = endDate).order_by("measuredOn")
 
    # Prepare data for history graph
    current_temp_array = []
    target_temp_array = []
    boiler_on_array = []
    boiler_off_array = []
    user_requested_temp_array = []
    ext_temp_array = []
    last_timestamp = 0
    delta_min = 10*60*1000  # Minimum interval in milliseconds between two points on graph
    for elt in queryset:
        #local_date = elt.measuredOn.astimezone(thermostat_timezone)
        #current_timestamp = time.mktime(local_date.timetuple()) * 1000  # Converts python datetime to javascript timestamp
        utc_date = elt.measuredOn.astimezone(pytz.utc)
        current_timestamp = time.mktime(utc_date.timetuple()) * 1000  # Converts to javascript timestamp
        if elt.T_ext is not None:
            if elt.T_ext > -50:
                ext_temp_array.append([current_timestamp, elt.T_ext])
        # Checks if time between elements is greater than delta_min        
        if (current_timestamp > last_timestamp + delta_min):
            last_timestamp = current_timestamp
            if elt.temperature > -50:
                current_temp_array.append([current_timestamp, elt.temperature])
            if elt.targetTemperature > -50:
                target_temp_array.append([current_timestamp, elt.targetTemperature])
            if elt.boilerOn:
                boiler_on_array.append([current_timestamp, elt.temperature])
                #boiler_off_array.append([current_timestamp, 0])
            else:
                #boiler_on_array.append([current_timestamp, 0])
                boiler_off_array.append([current_timestamp, elt.temperature])
            user_requested_temp_array.append([current_timestamp, elt.userRequestedTemperature])
            
    # Create array of days, for zoom buttons
    array_days = []
    index_day = 0
    localStartDate = startDate.astimezone(pytz.timezone(thermostat.timezone))
    localDate = localStartDate.replace(hour=0, minute=0, second=0)
    while localDate < endDate:
        localEndDate = localDate + timedelta(days=1)
        timestampStart = time.mktime(localDate.timetuple()) * 1000
        timestampEnd = time.mktime(localEndDate.timetuple()) * 1000        
        array_days.append({'start': timestampStart, 'end': timestampEnd, 'index': index_day})
        index_day += 1
        localDate = localEndDate
        
    # Computes heating speed statistics
    statistics = thermostat.stats_heating_speed(queryset)
    if statistics is not None:
        heating_speed_values = statistics['graph_values']
        heating_speed_at_7_degrees = float("{0:.1f}".format(statistics['value_at_7_degrees']))
        heating_speed_at_0_degrees = float("{0:.1f}".format(statistics['value_at_0_degrees']))
        heating_speed_at_all_temperatures = float("{0:.1f}".format(statistics['deriv_value_at_all_temperatures']))
        confiance_p_value = float("{0:.1f}".format( (1 - statistics['p_value'] ) * 100))
        if (heating_speed_at_7_degrees < 0.2):
            heating_speed_7_color = "red"
        else:
            heating_speed_7_color = "green"
        if (heating_speed_at_0_degrees < 0.2):
            heating_speed_0_color = "red"
        else:
            heating_speed_0_color = "green"
        if (heating_speed_at_all_temperatures < 0.2):
            heating_speed_all_color = "red"
        else:
            heating_speed_all_color = "green"
    else:
        heating_speed_values = []
        heating_speed_at_7_degrees = "ND"
        heating_speed_at_0_degrees = "ND"
        heating_speed_at_all_temperatures = "ND"
        heating_speed_7_color = ""
        heating_speed_0_color = ""
        heating_speed_all_color = ""
        confiance_p_value = "ND"

    # Computes boiler on statistics
    boiler_on_stats = thermostat.stats_boiler_on_time(queryset)
    boiler_on_time = boiler_on_stats['boiler_on_time']
    total_time = boiler_on_stats['total_time']
    if total_time > 0:
        percent_boiler_on = int(100 * boiler_on_time / total_time)
    else:
        percent_boiler_on = 0
        
    # Computes confort time statistics
    confort_stats = thermostat.stats_confort_time(queryset)
    percentage_confort = confort_stats['percentage_confort']
    if percentage_confort is None:
        percentage_confort = "ND"
        confort_color = ""
    else:
        if percentage_confort > 95:
            confort_color = "green"
        elif percentage_confort > 90:
            confort_color = "yellow"
        else:
            confort_color = "red"
        percentage_confort = str(int(percentage_confort)) + "%"
        
    # Computes timestamp for period before and period after (for "previous" and "next" buttons)
    period_before_timestamp = int(time.mktime(startDate.timetuple()) - (3600*24*number_of_days_in_graph))
    period_after_timestamp = int(time.mktime(endDate.timetuple()))
    
    context = RequestContext(request, {
        'thermostat': thermostat,
        'owner': thermostat.owner,
        'minutes_since_last_connection' : thermostat.minutes_since_last_connection(),
        'measured_temp': measured_temp,
        'userRequestedTemperature': userRequestedTemperature,
        'measured_temp_color': measured_temp_color,
        'boilerOn': boilerOn,
        'boilerOnColor': boilerOnColor,
        'title': "Thermostat : " + thermostat.name,
        'current_temp_array': json.dumps(current_temp_array),
        'target_temp_array': json.dumps(target_temp_array),
        'boiler_on_array': json.dumps(boiler_on_array),
        'boiler_off_array': json.dumps(boiler_off_array),
        'user_requested_temp_array': json.dumps(user_requested_temp_array),
        'ext_temp_array': json.dumps(ext_temp_array),
        'uid': uid,
        'number_of_days_in_graph': number_of_days_in_graph,
        'array_days': array_days,
        'heating_speed_values': heating_speed_values,
        'heating_speed_at_7_degrees': heating_speed_at_7_degrees,
        'heating_speed_at_0_degrees': heating_speed_at_0_degrees,
        'heating_speed_at_all_temperatures' : heating_speed_at_all_temperatures,
        'heating_speed_7_color': heating_speed_7_color,
        'heating_speed_0_color': heating_speed_0_color,
        'heating_speed_all_color' : heating_speed_all_color,
        'period_before_timestamp': period_before_timestamp,
        'period_after_timestamp': period_after_timestamp,
        'percent_boiler_on': percent_boiler_on,
        'percentage_confort': percentage_confort,
        'confort_color': confort_color,
        'confiance_p_value' : confiance_p_value,
        'username': request.user.username
    })
    
    template = loader.get_template('dashboard/thermostat.html')
    return HttpResponse(template.render(context))
       

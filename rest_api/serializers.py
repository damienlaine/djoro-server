from django.forms import widgets
from rest_framework import serializers
from django.contrib.auth.models import User
from thermostats.models import Thermostat, MeasuredTemp, TemperatureMode, WeekScheduleMarker, SpecialSchedule, SavingProposal
from django.db.models.query import QuerySet
import pytz
from datetime import datetime


class ThermostatSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    currentMeasuredTemp = serializers.SerializerMethodField('get_last_measured_temp')
    weekschedule = serializers.PrimaryKeyRelatedField(read_only=True)
    schedules = serializers.SerializerMethodField('get_current_schedules')
    savingProposalCount = serializers.SerializerMethodField('get_saving_proposal_number')
    
    def get_current_schedules(self, thermostat):
        # Get next schedules        
        next_schedules = thermostat.get_schedule()
        # Serialize the two firsts schedules (current and next)
        elt0 = next_schedules[0]
        serializer = TemperatureModeSerializer(elt0['temperatureMode'])
        elt0['temperatureMode'] = serializer.data
        elt1 = None
        if len(next_schedules) > 1:
            elt1 = next_schedules[1]
            serializer = TemperatureModeSerializer(elt1['temperatureMode'])
            elt1['temperatureMode'] = serializer.data
        return { 'current_schedule': elt0, 'next_schedule': elt1}
    
    def get_last_measured_temp(self, thermostat):
        queryset = thermostat.get_last_measured_temp()
        serializer = MeasuredTempSerializer(instance = queryset, many=False)
        return serializer.data

    def get_saving_proposal_number(self, thermostat):
        now=datetime.utcnow()
        now=now.replace(tzinfo=pytz.utc)
        return thermostat.savingproposal_set.filter(startValidityPeriod__lte=now, endValidityPeriod__gte=now, status__in=['PROP']).count()
    
    class Meta:
        model = Thermostat
        fields = ('id', 'name', 'totalSavingForPeriod', 'owner', 'currentMeasuredTemp', 'weekschedule', 'schedules', 'boilerOn', 'savingProposalCount')


class UserSerializer(serializers.ModelSerializer):
    thermostats = serializers.PrimaryKeyRelatedField(many=True, queryset=Thermostat.objects.all())

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'thermostats')


class MeasuredTempSerializer(serializers.ModelSerializer):

    class Meta:
        model = MeasuredTemp
        fields  = ('measuredOn', 'thermostat', 'temperature', 'manual', 'targetTemperature')

class MeasuredTempSerializerForCreation(serializers.ModelSerializer):
    
    class Meta:
        model = MeasuredTemp
        fields  = ('thermostat', 'temperature', 'manual', 'targetTemperature')
            

class TemperatureModeSerializer(serializers.ModelSerializer):

    class Meta:
        model = TemperatureMode
        fields  = ('id', 'internal_code', 'name', 'temperature', 'removable', 'thermostat')
        
        
class WeekScheduleMarkerSerializer(serializers.ModelSerializer):
    temperatureMode = TemperatureModeSerializer(read_only=True)

    class Meta:
        model = WeekScheduleMarker
        fields  = ('id', 'isoWeekDay', 'hour', 'minute', 'temperatureMode', 'weekSchedule')

class WeekScheduleMarkerSerializerForCreation(serializers.ModelSerializer):

    class Meta:
        model = WeekScheduleMarker
        fields  = ('id', 'isoWeekDay', 'hour', 'minute', 'temperatureMode', 'weekSchedule')

class SpecialScheduleSerializer(serializers.ModelSerializer):
    temperatureMode = TemperatureModeSerializer(read_only=True)
    localStartDate = serializers.SerializerMethodField('get_local_start_date')
    localEndDate = serializers.SerializerMethodField('get_local_end_date')
    
    def get_local_start_date(self, specialSchedule):        
        tz = pytz.timezone(specialSchedule.thermostat.timezone)
        return specialSchedule.startDate.astimezone(tz)

    def get_local_end_date(self, specialSchedule):        
        tz = pytz.timezone(specialSchedule.thermostat.timezone)
        return specialSchedule.endDate.astimezone(tz)
        
    def string_local_datetime_to_utc(self, instance, strDate):
        # Converts string date in local datetime to utc date
        tz = pytz.timezone(instance.thermostat.timezone)
        myDate = tz.localize(datetime.strptime(strDate, '%Y-%m-%dT%H:%M'))
        return myDate.astimezone(pytz.utc)        

    def update(self, instance, validated_data):
        # Converts localDates to UTC
        validated_data['startDate'] = self.string_local_datetime_to_utc(instance, self.context['localStartDate'])
        validated_data['endDate'] = self.string_local_datetime_to_utc(instance, self.context['localEndDate'])
        # Update nested object id
        validated_data['temperatureMode_id'] = self.context['temperatureMode']
        # Save instance
        return super(SpecialScheduleSerializer, self).update(instance, validated_data)

    class Meta:
        model = SpecialSchedule
        fields  = ('id', 'localStartDate', 'localEndDate', 'priority', 'thermostat', 'temperatureMode', 'savingProposal')
    
class SpecialScheduleSerializerForCreation(serializers.ModelSerializer):

    def string_local_datetime_to_utc(self, thermostat, strDate):
        # Converts string date in local datetime to utc date
        tz = pytz.timezone(thermostat.timezone)
        myDate = tz.localize(datetime.strptime(strDate, '%Y-%m-%dT%H:%M'))
        return myDate.astimezone(pytz.utc)        

    def create(self, validated_data):
        # Converts localDates to UTC
        thermostat = self.context['thermostat_instance']
        validated_data['startDate'] = self.string_local_datetime_to_utc(thermostat, self.context['localStartDate'])
        validated_data['endDate'] = self.string_local_datetime_to_utc(thermostat, self.context['localEndDate'])
        return super(SpecialScheduleSerializerForCreation, self).create(validated_data)        
        
    class Meta:
        model = SpecialSchedule
        fields  = ('id', 'priority', 'thermostat', 'temperatureMode', 'savingProposal')

class SpecialScheduleSerializerSetAway(serializers.ModelSerializer):

    def string_local_datetime_to_utc(self, thermostat, strDate):
        # Converts string date in local datetime to utc date
        tz = pytz.timezone(thermostat.timezone)
        myDate = tz.localize(datetime.strptime(strDate, '%Y-%m-%dT%H:%M'))
        return myDate.astimezone(pytz.utc)        

    def create(self, validated_data):
        thermostat = self.context['thermostat_instance']
        # Sets startDate to now
        validated_data['startDate'] = pytz.utc.localize(datetime.utcnow())
        # Converts localDate to UTC
        validated_data['endDate'] = self.string_local_datetime_to_utc(thermostat, self.context['localEndDate'])
        validated_data['temperatureMode'] = thermostat.temperaturemode_set.get(internal_code = self.context['temperatureModeCode'])
        validated_data['priority'] = 20
        return super(SpecialScheduleSerializerSetAway, self).create(validated_data)        
        
    class Meta:
        model = SpecialSchedule
        fields  = ('thermostat',)
        
        
class SavingProposalSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = SavingProposal
        fields  = ('id', 'type', 'status', 'parameter', 'messageWhenAccepted', 'startValidityPeriod', 'endValidityPeriod', 'title', 'content', 'amount', 'thermostat')
    
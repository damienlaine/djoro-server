from thermostats.models import Thermostat, MeasuredTemp, WeekScheduleMarker, TemperatureMode, SpecialSchedule, SavingProposal
from rest_api.serializers import ThermostatSerializer, WeekScheduleMarkerSerializer, WeekScheduleMarkerSerializerForCreation, TemperatureModeSerializer, SpecialScheduleSerializer, SpecialScheduleSerializerForCreation
from rest_api.serializers import  MeasuredTempSerializer, MeasuredTempSerializerForCreation, SpecialScheduleSerializerSetAway
from rest_api.serializers import UserSerializer, SavingProposalSerializer
from rest_framework import generics, viewsets
from django.contrib.auth.models import User
from rest_framework import permissions, status
from rest_api.permissions import IsOwner, IsMarkerOwner, IsSpecialScheduleOwner, TemperatureModePermission
from rest_framework.response import Response
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from serializers import TemperatureModeSerializer
from django.http import HttpResponse
from datetime import datetime
import pytz

import logging
from django.shortcuts import get_object_or_404

logger = logging.getLogger('djoro.thermostats')


class ThermostatList(generics.ListCreateAPIView):
    queryset = Thermostat.objects.all()
    serializer_class = ThermostatSerializer
    permission_classes = (permissions.IsAdminUser, )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ThermostatStatus(viewsets.ViewSet):
    
    permission_classes = (permissions.IsAuthenticated, IsOwner,)

    def retrieve(self, request, pk=None):
        queryset = Thermostat.objects.all()
        thermostat = get_object_or_404(queryset, pk=pk)
        self.check_object_permissions(self.request, thermostat)
        schedule = thermostat.get_schedule()
        # serialize temperatureMode objects
        for elt in schedule:
            serializer = TemperatureModeSerializer(elt['temperatureMode'])
            elt['temperatureMode'] = serializer.data
        return Response(schedule)

class ThermostatDetail(viewsets.ViewSet):
            
    logger.debug("in thermostat detail")
        
    queryset = Thermostat.objects.all()
    serializer_class = ThermostatSerializer
    permission_classes = (permissions.IsAuthenticated,)
    
    def retrieve(self, request, pk=None):
        try:            
            thermostat = Thermostat.objects.get(owner=request.user.id)
        except Thermostat.DoesNotExist:
            return HttpResponse('Unauthorized', status=401)
        
        serializer = ThermostatSerializer(thermostat)
        return Response(serializer.data)

class ThermostatHistory(viewsets.ViewSet):
    serializer_class = MeasuredTempSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwner,)
    
    def retrieve(self, request, pk=None):
        # Check permissions
        queryset = Thermostat.objects.all()
        thermostat = get_object_or_404(queryset, pk=pk)
        self.check_object_permissions(self.request, thermostat)
        # Get history        
        queryset = MeasuredTemp.objects.filter(thermostat = pk).order_by("-measuredOn")[0:5]
        serializer = MeasuredTempSerializer(queryset, many=True)
        return Response(serializer.data)

class DeviceStatus(viewsets.ViewSet):
    serializer_class = MeasuredTempSerializerForCreation
    
    def post(self, request):        
        """
        Post device status (api for hardware)
        Parameters to post : uid, apikey and temperature
        Returns coef and target_temp
        """
        logger.debug("in measured temp view POST op");
        logger.debug(request)
        logger.debug(request.data)
        queryset = Thermostat.objects.all()
        uid = request.data['uid']
        apikey = request.data['apikey']
        thermostat = get_object_or_404(queryset, uid=uid, apiKey = apikey)

        # Once per hour, get external temperature on openweathermap
        T_ext = None
        if (thermostat.is_time_to_get_external_temperature()):
            externalTemperatureObject = thermostat.get_openweathermap_external_temperature()
            # Store the datetime when we got external temperature. Note: even if the request failed, we will not try again before one hour
            thermostat.last_Text_date = datetime.utcnow().replace(tzinfo=pytz.utc)
            # Assign external temperature to T_ext variable
            if externalTemperatureObject is not None:
                T_ext = externalTemperatureObject['T']
                
        # get new measured temp data
        temperature = request.data['temperature']
        manual = request.data['manual']
        targetTemperature = request.data['tcons']
        boilerOn = request.data['boilerOn']
        
        # store the boilerOn status
        thermostat.boilerOn = request.data['boilerOn']

        # Get the schedule without anticipation
        raw_schedule = thermostat.get_raw_schedule()
        userRequestedTemperature = raw_schedule[0].get('temperatureMode').temperature
        print "User Requested Temperature", userRequestedTemperature

        # Store measured_temp
        measured_temp = thermostat.create_new_MeasuredTemp(temperature, manual, targetTemperature, boilerOn, T_ext, userRequestedTemperature)

        # update savings in euros
        thermostat.real_money_saved_calc()
        
        # Applies anticipation delays
        schedule = thermostat.controlparameters.applyAnticipation(raw_schedule)

        temperatureToApply = schedule[0].get('temperatureMode').temperature
        coef = thermostat.controlparameters.coef
        # Apply the proportional algorithm if needed (in final version, to be implemented in the device itself)
        if thermostat.controlparameters.prop_mode:
            # Computes the temperatureToApply for proportional algorithm
            temperatureToApply = thermostat.controlparameters.calculateProportional_T_target(temperature, temperatureToApply)
            
        # Apply derivative offset on target temperature
        temperatureToApply = temperatureToApply - thermostat.controlparameters.derivativeOffset(temperature)

        # Override targetTemperature
        # measured_temp.targetTemperature = temperatureToApply            

        # Save objects in database
        measured_temp.save()
        thermostat.save()
        
        return Response({"coef": coef, "target_temp": temperatureToApply});

class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class UserProfile(viewsets.ViewSet):
    
    def get(self, request):
        queryset = User.objects.all()        
        #check if the user is present in the db otherwize return 404 not found
        get_object_or_404(queryset, username = request.user.username)
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class WeekScheduleMarkerListCreate(viewsets.ViewSet):
    # Serializer for Create request (different from serializer for List request, because weekSchedule id has to be serialized as foreign key)   
    serializer_class = WeekScheduleMarkerSerializerForCreation
    permission_classes = (permissions.IsAuthenticated, IsOwner, )

    def get_list(self, request, pk=None):
        """
        This view should return a list of all the markers of the weekSchedule
        for the thermostat which id is passed in parameter
        """
        queryset = Thermostat.objects.all()
        thermostat = get_object_or_404(queryset, pk=pk)
        # Check permissions
        self.check_object_permissions(self.request, thermostat)        
        # Get weekSchedule        
        weekSchedule = thermostat.weekschedule
        markers = WeekScheduleMarker.objects.filter(weekSchedule=weekSchedule)
        # Serializer for List request (different from serializer for Create request)
        serializer = WeekScheduleMarkerSerializer(markers, many=True)
        return Response(serializer.data)
        
    def create(self, request, pk=None):
        # Find weekSchedule associated to the thermostat id
        queryset = Thermostat.objects.all()
        thermostat = get_object_or_404(queryset, pk=pk)
        # Check permissions
        self.check_object_permissions(self.request, thermostat)        
        # Get weekSchedule        
        weekSchedule = thermostat.weekschedule
        data = request.data
        data['weekSchedule'] = weekSchedule.pk
        serializer = WeekScheduleMarkerSerializerForCreation(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WeekScheduleMarkerDetail(generics.RetrieveUpdateAPIView, viewsets.ViewSet):
    queryset = WeekScheduleMarker.objects.all()
    # serializer_class = WeekScheduleMarkerSerializer
    permission_classes = (permissions.IsAuthenticated, IsMarkerOwner, )
    
    # Choose serializer according to action (don't want to serialize the temperature_mode for PUT)
    def get_serializer_class(self):
        if self.request.method.lower() == 'put':
            return WeekScheduleMarkerSerializerForCreation
        return WeekScheduleMarkerSerializer
    
    def delete(self, request, pk=None, pkt=None):
        queryset = WeekScheduleMarker.objects.all()
        marker = get_object_or_404(queryset, pk=pk)
        self.check_object_permissions(self.request, marker) 
        marker.delete()
        return Response({'detail':'WeekScheduleMarker deleted'}, status=status.HTTP_204_NO_CONTENT)
        
class SpecialScheduleListCreate(viewsets.ViewSet):
    # Serializer for Create request (different from serializer for List request, because weekSchedule id has to be serialized as foreign key)   
    serializer_class = SpecialScheduleSerializerForCreation
    permission_classes = (permissions.IsAuthenticated, IsOwner, )

    def get_list(self, request, pk=None):
        """
        This view should return a list of all the markers of the weekSchedule
        for the thermostat which id is passed in parameter
        """
        queryset = Thermostat.objects.all()
        thermostat = get_object_or_404(queryset, pk=pk)
        # Check permissions
        self.check_object_permissions(self.request, thermostat)
        now = datetime.now()     
        specialSchedules = SpecialSchedule.objects.filter(thermostat=thermostat, removed=False, endDate__gte = now).order_by('startDate')
        # Serializer for List request (different from serializer for Create request)
        serializer = SpecialScheduleSerializer(specialSchedules, many=True)
        return Response(serializer.data)

    def create(self, request, pk=None):
        # Find thermostat associated to the thermostat id
        queryset = Thermostat.objects.all()
        thermostat = get_object_or_404(queryset, pk=pk)
        # Check permissions
        self.check_object_permissions(self.request, thermostat)   
        data = request.data
        # Set thermostat id in specialSchedule to create
        data['thermostat'] = thermostat.id
        # Set thermostat instance to get it in the context
        data['thermostat_instance'] = thermostat
        serializer = SpecialScheduleSerializerForCreation(data=data, context=data)
        if serializer.is_valid():
            instance = serializer.save()
            serializer = SpecialScheduleSerializer(instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            #return Response({'detail':'Creation OK'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class SpecialScheduleDetail(generics.RetrieveAPIView, viewsets.ViewSet):
    queryset = SpecialSchedule.objects.all()
    permission_classes = (permissions.IsAuthenticated, IsSpecialScheduleOwner, )
        
    # Choose serializer according to action (don't want to serialize the temperature_mode for PUT)
    def get_serializer_class(self):
        if self.request.method.lower() == 'put':
            return SpecialScheduleSerializerForCreation
        return SpecialScheduleSerializer        
        
    def delete(self, request, pk=None, pkt=None):
        queryset = SpecialSchedule.objects.all()
        specialSchedule = get_object_or_404(queryset, id=pk)
        self.check_object_permissions(self.request, specialSchedule) 
        specialSchedule.removed = True
        specialSchedule.save()
        return Response({'detail':'SpecialSchedule deleted'}, status=status.HTTP_204_NO_CONTENT)
        
    def put(self, request, pk=None, pkt=None):
        queryset = SpecialSchedule.objects.all()
        specialSchedule = get_object_or_404(queryset, pk=pk)
        # Check that user owns the SpecialSchedule
        self.check_object_permissions(self.request, specialSchedule)        
        # Check that user does not bind the specialSchedule to another thermostat
        if (int(request.data['thermostat']) != specialSchedule.thermostat.pk):
            return HttpResponse('Unauthorized', status=401)
        serializer = SpecialScheduleSerializer(specialSchedule, data=request.data, context=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)        

class SpecialScheduleSetAway(viewsets.ViewSet):
    permission_classes = (permissions.IsAuthenticated, IsOwner, )

    def create(self, request, pk=None):
        # Find thermostat associated to the thermostat id
        queryset = Thermostat.objects.all()
        thermostat = get_object_or_404(queryset, pk=pk)
        # Check permissions
        self.check_object_permissions(self.request, thermostat)   
        data = request.data
        # Set thermostat id in specialSchedule to create
        data['thermostat'] = thermostat.id
        # Set thermostat instance to get it in the context
        data['thermostat_instance'] = thermostat
        serializer = SpecialScheduleSerializerSetAway(data=data, context=data)
        if serializer.is_valid():
            instance = serializer.save()
            serializer = SpecialScheduleSerializer(instance)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            #return Response({'detail':'Creation OK'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TemperatureModeListCreate(viewsets.ViewSet, generics.CreateAPIView):
    serializer_class = TemperatureModeSerializer
    permission_classes = (permissions.IsAuthenticated, TemperatureModePermission, )

    def get_list(self, request, pk=None):
        """
        This view should return a list of all the temperature modes
        for the thermostat which id is passed in parameter
        """
        queryset = Thermostat.objects.all()
        thermostat = get_object_or_404(queryset, pk=pk)
        # Check permissions
        self.check_object_permissions(self.request, thermostat)
        temperatureModes = thermostat.temperaturemode_set.filter(removed = False)
        serializer = TemperatureModeSerializer(temperatureModes, many=True)
        return Response(serializer.data)
        
    def post(self, request, *args, **kwargs):
        # Check permissions
        thermostat_pk = request.data['thermostat']
        queryset = Thermostat.objects.all()
        thermostat = get_object_or_404(queryset, pk=thermostat_pk)
        self.check_object_permissions(self.request, thermostat)
        # Execute herited method
        return generics.CreateAPIView.post(self, request, *args, **kwargs)

#class TemperatureModeDetail(generics.RetrieveUpdateAPIView, generics.CreateAPIView, viewsets.ViewSet): # Create was here by mistake ? Check if it's ok then delete this line
class TemperatureModeDetail(generics.RetrieveUpdateAPIView, viewsets.ViewSet):
    queryset = TemperatureMode.objects.all()
    serializer_class = TemperatureModeSerializer
    permission_classes = (permissions.IsAuthenticated, TemperatureModePermission, )
    
    def delete(self, request, pk=None):
        queryset = TemperatureMode.objects.all()
        temperatureMode = get_object_or_404(queryset, pk=pk)
        # Check permissions
        self.check_object_permissions(self.request, temperatureMode)
        # Check if object is removable
        if (temperatureMode.removable == True):
            temperatureMode.removed = True
            temperatureMode.save()
            return Response({'detail':'TemperatureMode deleted'}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({'detail':'TemperatureMode not removable'}, status=status.HTTP_403_FORBIDDEN)

    def put(self, request, *args, **kwargs):
        # Check that user owns the TemperatureMode
        temperatureMode = self.get_object()
        self.check_object_permissions(self.request, temperatureMode)        
        # Check that user does not bind the temperature mode to another thermostat
        if (int(request.data['thermostat']) != temperatureMode.thermostat.pk):
            return HttpResponse('Unauthorized', status=401)
        # Execute herited method to update thermostat
        return generics.RetrieveUpdateAPIView.put(self, request, *args, **kwargs)

class SavingProposalList(viewsets.ViewSet):
    serializer_class = SavingProposalSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwner,)
    
    def retrieve(self, request, pk=None):
        # Check permissions
        queryset = Thermostat.objects.all()
        thermostat = get_object_or_404(queryset, pk=pk)
        self.check_object_permissions(self.request, thermostat)
        # Get saving proposals
        now=datetime.utcnow()
        now=now.replace(tzinfo=pytz.utc)
        queryset = SavingProposal.objects.filter(thermostat = pk, startValidityPeriod__lte=now, endValidityPeriod__gte=now, status__in=['PROP'])
        serializer = SavingProposalSerializer(queryset, many=True)
        return Response(serializer.data)

class SavingProposalRemoveApply(viewsets.ViewSet):
    serializer_class = SavingProposalSerializer
    permission_classes = (permissions.IsAuthenticated, IsOwner,)
    
    def delete(self, request, pkt=None, pk=None):
        queryset = SavingProposal.objects.all()
        savingProposal = get_object_or_404(queryset, pk=pk)
        # Check permissions
        self.check_object_permissions(self.request, savingProposal)
        # Dismiss savingProposal
        savingProposal.dismiss()
        return Response({'detail':'Saving proposal dismissed'}, status=status.HTTP_204_NO_CONTENT)

    def apply(self, request, pkt=None, pk=None):
        queryset = SavingProposal.objects.all()
        savingProposal = get_object_or_404(queryset, pk=pk)
        # Check permissions
        self.check_object_permissions(self.request, savingProposal)
        # Apply savingProposal
        savingProposal.applySaving()
        return Response({'detail':'Saving proposal applied'}, status=status.HTTP_200_OK)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)

from rest_framework import permissions
from thermostats.models import Thermostat
import logging

logger = logging.getLogger(__name__)

class IsOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to read it.
    """

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Thermostat):
            return obj.owner == request.user
        return obj.thermostat.owner == request.user

class IsMarkerOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        pkt = view.kwargs['pkt']
        # Find thermostat associated to the thermostat id passed in the request, to check if it belongs to user
        try:
            thermostat = Thermostat.objects.get(pk=pkt)
        except Thermostat.DoesNotExist:
            return False
        # Checks if thermostat belongs to user            
        return thermostat.owner == request.user
        
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return obj.weekSchedule.thermostat.owner == request.user 

class IsSpecialScheduleOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        pkt = view.kwargs['pkt']
        # Find thermostat associated to the thermostat id passed in the request, to check if it belongs to user
        try:
            thermostat = Thermostat.objects.get(pk=pkt)
        except Thermostat.DoesNotExist:
            return False
        # Checks if thermostat belongs to user            
        return thermostat.owner == request.user
        
    def has_object_permission(self, request, view, obj):
        """
        Return `True` if permission is granted, `False` otherwise.
        """
        return obj.thermostat.owner == request.user 
        
class TemperatureModePermission(permissions.BasePermission):        
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Thermostat):
            return obj.owner == request.user
        # If it is not a thermostat, it is a TemperatureMode
        return obj.thermostat.owner == request.user

"""
class IsOwnerOrReadOnly(permissions.BasePermission):
    # Custom permission to only allow owners of an object to edit it.

    def has_object_permission(self, request, view, obj):
        logger.debug('test permissions')
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        return obj.owner == request.user
"""
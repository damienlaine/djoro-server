# -*- coding: utf-8 -*-

from rest_framework.authtoken.views import ObtainAuthToken

from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.response import Response
from django.contrib.auth.models import User
from thermostats.models import Thermostat
from django.shortcuts import get_object_or_404

"""
class ObtainAuthToken():
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)

    def post(self, request):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})


obtain_auth_token = ObtainAuthToken.as_view()
"""
class DjoroObtainAuthToken(ObtainAuthToken):
    
    def post(self, request):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        # Get User object to fetch thermostat id
        queryset = User.objects.all()        
        # User should exist, so this should never return 404
        userObject = get_object_or_404(queryset, username = request.data['username'])        
        # Get thermostat object
        queryset = Thermostat.objects.all()
        thermostat = get_object_or_404(queryset, owner = userObject.id)        
        
        return Response({'token': token.key, 'thermostatId': thermostat.id})
        
djoro_obtain_auth_token = DjoroObtainAuthToken.as_view()
# -*- coding: utf-8 -*-

from thermostats.models import Thermostat, ProfessionalUser
import logging

logger = logging.getLogger(__name__)

def is_professional(user):
    return ProfessionalUser.objects.filter(user_id = user.pk).exists()

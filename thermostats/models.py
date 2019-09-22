# -*- coding: utf-8 -*- 
from django.db import models
import logging
from django.template.defaultfilters import default
import datetime
import utils.mydate
import pytz
import requests
import json
from django.core.exceptions import ObjectDoesNotExist
from scipy import stats
import time

logger = logging.getLogger('djoro.thermostats')

class ProfessionalUser(models.Model):
    user = models.ForeignKey('auth.User')

    def __unicode__(self):
        return '%s' % (self.user.username)


class Thermostat(models.Model):
    createdOn = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100, blank=True, default='')
    owner = models.ForeignKey('auth.User', related_name='thermostats')
    professionalOwner = models.ForeignKey('ProfessionalUser', default=None, null=True)
    timezone = models.CharField(max_length=100, default='Europe/Paris')
    address = models.CharField(max_length=1024, blank=True, default='')
    latitude = models.CharField(max_length=100, default = '43.60')
    longitude = models.CharField(max_length=100, default = '1.43')
    uid = models.CharField(max_length=128, blank=True, default='')
    apiKey = models.CharField(max_length=128, blank=True, default='')
    startSavingPeriod = models.DateTimeField()
    totalSavingForPeriod = models.FloatField(default=0.0)
    boilerOn = models.BooleanField(default=False)
    last_Text_date = models.DateTimeField(default=datetime.datetime(2010, 01, 01, 0, 0))
    last_maintenance_date = models.DateField(default=datetime.date(2010,01,01))
    
    class Meta:
        ordering = ('createdOn',)

    def __unicode__(self):              # __unicode__ on Python 2
        return self.name
    
    def now(self):
        tz = pytz.timezone(self.timezone)
        #now = utils.mydate.now(pytz.utc)
        now = utils.mydate.now(tz)     
        return now

    def save(self, *args, **kwargs):
        """
        Overriding the save method for example purpose.
        """
        #logger.debug('Thermostat saved')
        super(Thermostat, self).save(*args, **kwargs)
        
    def stats_heating_speed(self, measuredtemp_queryset):
        """
        Calculates the heating speed on the measuredtemp queryset,
        and returns calculated speed when external temperature is -7°C, 0°C, 7°C and 15°C
        """
        # Constants
        min_data_number = 10    # Minimum number of points to make the regression
        min_heating_time_seconds = 4 * 3600 # Minimum heating time in seconds to compute statistics
        min_interval = 240      # Minimum number of seconds between two points (in order to avoid issues of measurement precision, and getting many points where dT/dt = 0)
        max_interval = 1800     # Maximum number of seconds between two points (if interval is greater, it means that we had a deconnexion)
        # Creates arrays: Tint derivative and T_ext
        old_Tint = None
        old_timestamp = None
        old_boilerOn = None
        T_ext = None
        array_derivTint = []
        array_T_ext = []
        total_T_elevation = 0.0
        total_time = 0
        for elt in measuredtemp_queryset:
            # Keeps track of last measured T_ext (because T_ext is not recorded at every step)            
            if elt.T_ext is not None:
                if elt.T_ext > -50:
                    T_ext = elt.T_ext

            # Get timestamp of measurement
            utc_date = elt.measuredOn.astimezone(pytz.utc)
            current_timestamp = time.mktime(utc_date.timetuple())
            # Calculates only every min_interval seconds
            if old_timestamp is not None:
                if current_timestamp > old_timestamp + min_interval:                        
                    # Calculation of heating speed is done only when boiler is on            
                    if old_boilerOn:
                        # Computes derivative of Tint
                        derivTint = 3600 * float(elt.temperature - old_Tint) / (current_timestamp - old_timestamp)
                        # Computes total elevation and total time
                        total_T_elevation += elt.temperature - old_Tint
                        total_time += current_timestamp - old_timestamp
                        # Push result in arrays only if time interval is not too long
                        if (T_ext is not None) and (current_timestamp < old_timestamp + max_interval) :
                            array_derivTint.append(derivTint)
                            array_T_ext.append(T_ext)
                        # Keeps values for next loop
                    old_Tint = elt.temperature
                    old_timestamp = current_timestamp
                    old_boilerOn = elt.boilerOn
            else:
                old_timestamp = current_timestamp
        # Checks if we have enough data
        if (len(array_derivTint) < min_data_number) or (total_time < min_heating_time_seconds):
            return None
        else:
            # Make the linear regression        
            slope, intercept, r_value, p_value, std_err = stats.linregress(array_T_ext, array_derivTint)
            # Computes total derivative
            deriv_value_at_all_temperatures = 0
            if (total_time > 0):
                deriv_value_at_all_temperatures = 3600 * float(total_T_elevation) / total_time
            return {
                    "graph_values": [ [ -7 , -7*slope + intercept ], [0, intercept], [ 7, 7*slope + intercept], [15, 15*slope + intercept] ],
                    "value_at_7_degrees": 7*slope + intercept,
                    "value_at_0_degrees": intercept,
                    "slope": slope,
                    "intercept": intercept,
                    "r_value": r_value,
                    "p_value": p_value,
                    "std_err": std_err,
                    "deriv_value_at_all_temperatures": deriv_value_at_all_temperatures
                }
    
    def stats_boiler_on_time(self, measuredtemp_queryset):
        """
        Computes boiler_on and boiler_off time, in seconds
        """            
        # Constants
        max_interval = 1800     # Maximum number of seconds between two points (if interval is greater, it means that we had a deconnexion)
        # Computation variables
        old_timestamp = None
        boiler_on_time = 0
        boiler_off_time = 0
        for elt in measuredtemp_queryset:
            # Get timestamp of measurement
            utc_date = elt.measuredOn.astimezone(pytz.utc)
            current_timestamp = time.mktime(utc_date.timetuple())
            if old_timestamp is not None:
                interval = current_timestamp - old_timestamp
                # Checks if we didn't exceed max interval between two points (deconnexion)
                if interval < max_interval:                        
                    if elt.boilerOn:
                        boiler_on_time += interval
                    else:
                        boiler_off_time += interval
                # Keeps value for next loop
                old_timestamp = current_timestamp
            else:
                old_timestamp = current_timestamp
        return  {
            "boiler_on_time": boiler_on_time,
            "boiler_off_time": boiler_off_time,
            "total_time": boiler_on_time + boiler_off_time
            }

    def stats_confort_time(self, measuredtemp_queryset):
        """
        Computes time during which user requested temperature has not been reached, in seconds
        """            
        # Constants
        max_interval = 1800     # Maximum number of seconds between two points (if interval is greater, it means that we had a deconnexion)
        confort_temp_margin = 0.5   # Margin under which we consider that user requested temperature has not been reached (example: 0.5 => 19.5° is OK for 20° requested)
        # Computation variables
        old_timestamp = None
        confort_time = 0
        unconfort_time = 0
        for elt in measuredtemp_queryset:
            # Get timestamp of measurement
            utc_date = elt.measuredOn.astimezone(pytz.utc)
            current_timestamp = time.mktime(utc_date.timetuple())
            if old_timestamp is not None:
                interval = current_timestamp - old_timestamp
                # Checks if we didn't exceed max interval between two points (deconnexion)
                if (interval < max_interval) and (elt.userRequestedTemperature is not None):                        
                    if elt.temperature < elt.userRequestedTemperature - confort_temp_margin:
                        unconfort_time += interval
                    else:
                        confort_time += interval
                # Keeps value for next loop
                old_timestamp = current_timestamp
            else:
                old_timestamp = current_timestamp
        # Computes percentage
        total_time = confort_time + unconfort_time
        if total_time > 0:
            percentage_confort = 100 * confort_time / total_time
        else:
            percentage_confort = None
        return  {
            "confort_time": confort_time,
            "unconfort_time": unconfort_time,
            "total_time": total_time,
            "percentage_confort": percentage_confort
            }
                
        
    def get_last_measured_temp(self):
        return self.measuredtemp_set.last()
        
    ##
    # Returns time since last connection in minutes
    #
    def minutes_since_last_connection(self):
        last_measurement = self.get_last_measured_temp()
        if last_measurement is None:
            return None
        now = utils.mydate.now(pytz.UTC)
        delta_minutes = int((now - last_measurement.measuredOn).total_seconds() / 60)
        return delta_minutes
        
    def is_time_to_get_external_temperature(self):
        """
        Returns true if it is time to get external temperature (once per hour)
        """
        # Calculate number of seconds since last hit to openweathermap server
        delta_seconds = (datetime.datetime.utcnow().replace(tzinfo=pytz.utc) - self.last_Text_date).total_seconds()
        print "Nombre de secondes depuis la dernière fois:", delta_seconds
        if (delta_seconds > 3600):
            return True
        else:
            return False
        
    def get_openweathermap_external_temperature(self):
        """
        Get external temperature on openweathermap
        """
        url = "http://api.openweathermap.org/data/2.5/weather/?lat=" + self.latitude + "&lon=" + self.longitude + "&mode=json&APPID=53c2d72826f2215d60c154f657ddb923"
        try:
            r = requests.get(url)
        except requests.exceptions.RequestException:
            return None
            
        resultat = None
        if (r.status_code == 200):
            data = json.loads(r.content)
            ech_ts_date = data['dt']
            ech_date = datetime.datetime.utcfromtimestamp(ech_ts_date) # Convertit le timestamp en date
            ech_date = ech_date.replace(tzinfo=pytz.utc)
            # Récupère la température en Kelvin et convertit en °C                
            ech_temp = data['main']['temp'] - 273.15

            # Construit l'élément                
            resultat = {
                'date': ech_date,
                'T': ech_temp,
            }

        return resultat
        
    def create_new_MeasuredTemp(self, temperature, manual, targetTemperature, boilerOn, T_ext, userRequestedTemperature):
        # Get time in utc
        now =  utils.mydate.now(pytz.UTC)
        newMeasuredTemp = self.measuredtemp_set.create(measuredOn=now, temperature=temperature, manual=manual, targetTemperature=targetTemperature, boilerOn=boilerOn, T_ext=T_ext, userRequestedTemperature=userRequestedTemperature)
        # Don't save record in the database, this will be done by the calling method
        #newMeasuredTemp.save()
        return newMeasuredTemp
        
    ##
    # Computes money saved since last calculation step
    # Updates self.totalSavingForPeriod and creates a SavingHistory object
    # (The SavingHistory object stores one calculation step, while the totalSavingForPeriod stores the total amount saved since the beginning)
    #
    def real_money_saved_calc(self):

        now = utils.mydate.now(pytz.UTC)

        # Get the last element of saving history
        first_time = False
        try:
            last_saving_history = self.savinghistory_set.latest('endDate')            
        except ObjectDoesNotExist:
            # If this is the first time we calculate the savings, we will just update the date. No calculation.
            first_time = True
        
        if not first_time:
            # Get startDate from last record (last record endDate = new record startDate)
            startDate = last_saving_history.endDate
            # Get base temperature
            base_temp = 22  # TODO mettre ça dans un fichier de paramètres quelque part
            # Calculate number of days since last calculation
            timedelta = now - last_saving_history.endDate
            deltadays = timedelta.days + (float(timedelta.seconds) / 86400)
            # Get the cost of a DJU
            dju_cost = self.building_parameters.getDJUPrice()
            # Get the last measured temperature
            try:
                current_temperature = self.measuredtemp_set.latest('measuredOn').temperature
            except ObjectDoesNotExist:
                current_temperature = -99.0
            # Check if current_temperature is valid
            if current_temperature > -90.0:
                # Calculate new cost savings
                new_cost_savings = max ((base_temp - current_temperature) , 0) * deltadays * dju_cost
                # Update total cost savings
                self.totalSavingForPeriod += new_cost_savings
            else:
                # Temperature not valid
                new_cost_savings = None
            #print "Current_temp : ", current_temperature
            #print "new_cost_savings: ", new_cost_savings
        else:
            new_cost_savings = 0
            startDate = now
            
        # Update last_calc_date
        # Record the current calculation in history

        new_saving_history = self.savinghistory_set.create(startDate = startDate, endDate = now, saving = new_cost_savings) # TODO affecter le bon specialSchedule
        # Save records in the database
        new_saving_history.save()
        self.save()

        return self.totalSavingForPeriod

    ##    
    # Renvoie les températures de consigne à appliquer pour les 24 prochaines heures
    # Avec anticipation de chauffe
    #    
    def get_schedule(self):
        next_schedules = self.get_raw_schedule()        
        # Applies anticipation delays
        next_schedules_anticipate = self.controlparameters.applyAnticipation(next_schedules)
        return next_schedules_anticipate
        
    ##    
    # Renvoie les températures de consigne à appliquer pour les 24 prochaines heures
    # Sans anticipation de chauffe
    #    
    def get_raw_schedule(self):
        # Récupère l'heure actuelle
        now = self.now()
        
        # Récupère la timezone de l'utilisateur        
        tz = pytz.timezone(self.timezone)
            
        # On commence par les SpecialSchedule
        specialSchedules = self.specialschedule_set.filter(removed=False)        
                            
        # Crée une liste qui contiendra tous les changements de Tconsigne programmés, quelque soit leur priorité
        changements = []
        # Itère sur les savings
        schedule_i = 0
        for schedule in specialSchedules:
            # Incrémente l'indice identifiant le schedule
            schedule_i = schedule_i + 1
            # Récupère le programme contenu dans le schedule
#            logger.debug('start-date: %s, end-date: %s, now : %s,  now_aware: %s' % (schedule.startDate, schedule.endDate, now, now_aware))
            # Vérifie si le programme est applicable (ie déjà démarré ou démarre dans moins de 24h, pas encore terminé, et validé)
#            print "startDate 1 : ", schedule.startDate         
#            tz = pytz.timezone(self.timezone)
#            schedule.startDate = schedule.startDate.astimezone(tz)
#            print "startDate 2 : ", schedule.startDate
            if ((schedule.startDate - datetime.timedelta(days=1)) <= now < schedule.endDate):    

                # Calcule le nombre de minutes avant le début du programme
                if schedule.startDate < now:
                    # Le programme est déjà démarré
                    delta_minutes_debut = 0
                else:
                    # Le programme démarre plus tard. Calcule dans combien de minutes il démarre.
                    timedelta_debut = schedule.startDate - now
                    delta_minutes_debut = (timedelta_debut.days * 24 * 60) + ( (timedelta_debut.seconds + 59) / 60) # on ajoute 59 secondes car on veut qu'un delta de 1s soit arrondi à 1 minute
                # Convertit les datetimes en heure locale
                schedule.startDate = tz.normalize(schedule.startDate.astimezone(tz))
                schedule.endDate = tz.normalize(schedule.endDate.astimezone(tz))
                # Ajoute le programme sous la forme d'un unique point de consigne à appliquer immédiatement...
                changements.append({'datetime': schedule.startDate, 'minutes': delta_minutes_debut, 'schedule_i': schedule_i, 'special_schedule_id': schedule.id, 'priority': schedule.priority, 'temperatureMode': schedule.temperatureMode })
                # ... et d'une fin de programme à la fin de validité de celui-ci
                timedelta = schedule.endDate - now
                delta_minutes = (timedelta.days * 24 * 60) + ( (timedelta.seconds + 59) / 60)   # temps en minutes entre maintenant et la fin du programme (on ajoute 59 secondes car on veut qu'un delta de 1s soit arrondi à 1 minute)
                changements.append({'datetime': schedule.endDate, 'minutes': delta_minutes, 'schedule_i': schedule_i, 'special_schedule_id': None, 'priority': schedule.priority, 'temperatureMode': None })                                
        #endfor
        
        # On s'occupe maintenant du WeekSchedule
        schedule = None # We don't use schedule anymore            
        schedule_i = schedule_i + 1
        week_schedule = self.weekschedule
        # Récupère la dernière température applicable à la date/heure de maintenant...
        temp_now = week_schedule.get_last_week_temp(now)
        # ... et l'ajoute au programme
        changements.append({'datetime': now, 'minutes': 0, 'schedule_i': schedule_i, 'special_schedule_id': None, 'priority': 0, 'temperatureMode': temp_now })
        # Récupère les prochaines températures applicables pour les 24 prochaines heures
        liste_temp_suivantes = week_schedule.get_next_24h_change(now)                        
        # ... et les ajoute au programme
        for elt in liste_temp_suivantes:
            temperatureMode = elt['temperatureMode']
            date_application = elt['datetime_application']
            #logger.debug('date_application: %s, now: %s ' % (date_application, now)) 
            timedelta = date_application - now
            delta_minutes = (timedelta.days * 24 * 60) + ( (timedelta.seconds + 59) / 60)   # On ajoute 59 secondes car on veut qu'un delta de 1s soit arrondi à 1 minute
            changements.append({'datetime': date_application, 'minutes': delta_minutes, 'schedule_i': schedule_i, 'special_schedule_id': None, 'priority': 0, 'temperatureMode': temperatureMode })                                 
        # Parcourt la liste des changements de consigne programmés dans l'ordre et en déduit la température applicable à chaque instant pour chaque schedule       
        # Trie la liste des changements par ordre chronologique        
        changements = sorted(changements, key=lambda k: k['minutes']) 
        # Initialise un tableau contenant les consignes en cours pour chaque schedule        
        en_cours_par_saving_i = {}
        # Initialise le schedule en cours
        saving_en_cours = None
        # Initialise le résultat
        resultat_inter = {}
        # Parcourt la liste des changements dans l'ordre
        for changement in changements:
            saving_fini = False
            minutes_fini = 0
            if (changement['temperatureMode'] == None):
                # Si le schedule est fini, le retire de la liste en_cours, et mémorise l'heure à laquelle il s'est terminé
                try:
                    en_cours_par_saving_i.pop(changement['schedule_i'])
                    if changement['schedule_i'] == saving_en_cours['schedule_i']:
                        minutes_fini = changement['minutes']                        
                        saving_fini = True
                        saving_en_cours = None
                except:
                    None
            else:
                # Si le schedule n'est pas fini (Température valide), l'insère dans la liste en_cours
                en_cours_par_saving_i[changement['schedule_i']] = changement

            # Récupère la consigne la plus prioritaire dans la liste en_cours
            for elt in en_cours_par_saving_i:
                mybool = False
                if (not saving_en_cours):
                    mybool = True                    
                elif  (en_cours_par_saving_i[elt]['priority'] >= saving_en_cours['priority'] ):
                    mybool = True
                if mybool:
                    saving_en_cours = en_cours_par_saving_i[elt]
            
            # On a fini de déterminer quel est le schedule en cours à l'instant t       
            
            # Détermine l'instant t
            if saving_fini:
                # Si c'est la fin d'un schedule
                minutes = minutes_fini
            else:
                # Sinon, c'est qu'on est au début d'un nouveau schedule
                minutes = saving_en_cours['minutes']            
            
            # Stocke le résultat intermédiaire sous forme de dictionnaire
            if (saving_en_cours is None):
                resultat_inter[minutes] = {}
            else:
                # Stocke la date et l'heure du changement de consigne, en ne gardant que la date/heure du premier changement pour un saving donné dans l'ordre chronologique
                if minutes in resultat_inter :
                    datetime_changement = resultat_inter[minutes]['datetime']
                else:
                    datetime_changement = changement['datetime']

                # Indicates which saving has to start in n minutes
                resultat_inter[minutes] = saving_en_cours
                # Indicates at what time this saving has to start
                resultat_inter[minutes]['datetime'] = datetime_changement
            
        # Transforme le résultat intermédiaire (dico) sous la forme finale (liste de tuples), en supprimant les doublons
        temperature_en_cours = None
        resultat = []
        for minutes in sorted(resultat_inter.iterkeys()):
            # Ne renvoie que les prochaines 24h
            if (minutes < 1440):
                if (resultat_inter[minutes]['temperatureMode'] != temperature_en_cours):
                    #print "resultat_inter: ", resultat_inter[minutes]
                    temperature_en_cours = resultat_inter[minutes]['temperatureMode']
                    datetime_en_cours = resultat_inter[minutes]['datetime']
                    special_schedule_id_en_cours = resultat_inter[minutes]['special_schedule_id']
                    resultat.append({'datetime': datetime_en_cours, 'minutes': minutes, 'temperatureMode': temperature_en_cours, 'specialSchedule_id': special_schedule_id_en_cours})
                       
        # Renvoie le résultat
        return resultat


class TemperatureMode(models.Model):
    COMFORT = 'COMF'
    AWAY = 'AWAY'
    NIGHT = 'NIGH'
    CUSTOM = 'CUST'
    TEMP_MODE_CHOICES = (
        (COMFORT, 'Confort'),
        (AWAY, 'Absent'),
        (NIGHT, 'Nuit'),
        (CUSTOM, 'Custom')
    )
    internal_code = models.CharField(max_length=4,
                          choices=TEMP_MODE_CHOICES,
                          default=CUSTOM)
    name = models.CharField(max_length=100, blank=False, default='Température Utilisateur')
    temperature = models.FloatField()
    removable = models.BooleanField(default=True)
    removed = models.BooleanField(default=False)    # TemperatureMode must not be deleted. We flag them as "removed" instead.
    thermostat = models.ForeignKey('Thermostat')
    
    def __unicode__(self):
        return "%s,%s" % (self.name, self.thermostat.name)

class MeasuredTemp(models.Model):
    measuredOn = models.DateTimeField()
    thermostat = models.ForeignKey('Thermostat')
    temperature = models.FloatField(default=-99.0)
    manual = models.BooleanField(default=False)
    targetTemperature = models.FloatField(default=-99.0)
    userRequestedTemperature = models.FloatField(default=None, blank=True, null=True) # Temperature requested by user (without anticipation)
    T_ext = models.FloatField(default=None, blank=True, null=True)
    boilerOn = models.BooleanField(default=False)

    def __unicode__(self):
        return '%s,%s,%f,%r,%f' % (self.measuredOn, self.thermostat.name, self.temperature, self.manual, self.targetTemperature)
        
class BuildingParameters(models.Model):
    annualEnergyBill = models.FloatField()
    annualSubscriptionAmount = models.FloatField()
    
    ELEC = 'ELEC'
    GAS = 'GAS'
    OIL = 'OIL'
    BOILER_TYPE_CHOICES = (
        (GAS, 'Gaz'),
        (OIL, 'Fuel'),
        (ELEC, 'Electrique')
    )
    boilerType = models.CharField(max_length=4,
                          choices=BOILER_TYPE_CHOICES,
                          default=GAS)
    dju = models.FloatField()
    thermostat = models.OneToOneField('Thermostat', primary_key=True, related_name='building_parameters')

    # return euros/dju
    def getDJUPrice(self):
        heatingPercentage = 0.0
        if (self.boilerType == self.ELEC):
            heatingPercentage = 0.7
        elif (self.boilerType == self.GAS):
            heatingPercentage = 0.81
        elif (self.boilerType == self.OIL):
            heatingPercentage = 0.87

        return (self.annualEnergyBill - self.annualSubscriptionAmount) * heatingPercentage / self.dju
    
    def __unicode__(self):
        return '%s, %f, %f, %s, %f' % (self.thermostat.name, self.annualEnergyBill, self.annualSubscriptionAmount, self.boilerType, self.dju)
    
    


class SetPointHistory(models.Model):
    createdOn = models.DateTimeField(auto_now_add=True)
    temperature = models.FloatField()
    modeName = models.CharField(max_length=100)
    modeInternalCode = models.CharField(max_length=4)
    thermostat = models.ForeignKey('Thermostat', related_name='set_point_history')
    
class ControlParameters(models.Model):
    coef = models.FloatField(default=0.1)   # Hysteresis factor
    anticipation_coef = models.FloatField(default=90) # in minutes
    anticipation_exp = models.FloatField(default=1)
    anticipation_max_hours = models.FloatField(default=8)
    deriv_coef = models.FloatField(default=0) # Derivative coefficient (in minutes), used to extrapolate Tint for a certain number of minutes, which can be important for high delay heating systems
    prop_mode = models.BooleanField(default=False) # Proportional control mode
    prop_duration = models.FloatField(default=20) # Duration of proportional band in minutes
    prop_minimum_on_time = models.FloatField(default=7) # Minimum on-time in proportional mode
    prop_minimum_off_time = models.FloatField(default=3) # Minimum off-time in proportional mode
    prop_band_half_width = models.FloatField(default=1) # Half width of proportional band, in degrees
    prop_start_off_phase_date = models.DateTimeField(default=datetime.datetime(2010, 01, 01, 0, 0, tzinfo=pytz.utc)) # Date when we have to switch to boiler_off mode
    prop_end_cycle_date = models.DateTimeField(default=datetime.datetime(2010, 01, 01, 0, 0, tzinfo=pytz.utc)) # Date when the cycle has to stop
    
    thermostat = models.OneToOneField('Thermostat', primary_key=True)

    # Calculates derivative offset (degrees to add to Tint if we want to extrapolate for "deriv_coef" minutes)
    def derivativeOffset(self, Tnow):
        if self.deriv_coef == 0:
            # If we don't want to use derivative offset
            return 0.0
        now =  utils.mydate.now(pytz.UTC)
        now_minus_30min = now - datetime.timedelta(seconds=1800)
        now_minus_1h = now - datetime.timedelta(seconds=3600)
        measured_before = self.thermostat.measuredtemp_set.filter(measuredOn__gte = now_minus_1h, measuredOn__lte = now_minus_30min).last()
        #measured_before = self.thermostat.measuredtemp_set.last()
        if measured_before is None:
            # If we don't have a measure, return 0
            return 0.0
        # Else computes derivative
        deltaT = Tnow - measured_before.temperature
        deltaMinutes = (now - measured_before.measuredOn).seconds / 60
        derivative = float(deltaT) / deltaMinutes # In °C / minute
        temperature_offset = derivative * self.deriv_coef
        return temperature_offset
    
    # Calculates anticipation delay
    def anticipationDelay(self, Tint, Ttarget):
        if (Ttarget > Tint):
            return min( self.anticipation_coef* ((Ttarget - Tint)**self.anticipation_exp), self.anticipation_max_hours*60 )
        else:
            return 0

    # Applies anticipation delay on next_schedules list
    # In this method, Tint is taken in last measuredTemp object
    def applyAnticipation(self, next_schedules):
        T_int = self.thermostat.get_last_measured_temp().temperature
        # Calculate extrapolate T_int (taking into account derivative_offset)
        extrapolate_T_int = T_int + self.derivativeOffset(T_int)
        return self.applyAnticipationTint(next_schedules, extrapolate_T_int)

    # Applies anticipation delay on next_schedules list
    # In this method, Tint is given in parameter (this enables to use an extrapolation of Tint to take delay into account)
    def applyAnticipationTint(self, next_schedules, Tint):
        for schedule in next_schedules:
            schedule['minutes'] = max(schedule['minutes'] - self.anticipationDelay(Tint, schedule['temperatureMode'].temperature), 0)
            schedule['preheat'] = False
        # Checks if a next schedule has to be applied right now
        preheat_schedule = None
        last_max_temperature = next_schedules[0]['temperatureMode'].temperature
        for idx, schedule in enumerate(next_schedules):
            if idx != 0:
                # Checks if preheat has to be applied now for this next schedule
                if schedule['minutes'] == 0:
                    if schedule['temperatureMode'].temperature > last_max_temperature:
                        schedule['preheat'] = True
                        preheat_schedule = schedule
        # If preheat has to be applied now, returns the preheat schedule to apply
        if preheat_schedule != None:
            return [preheat_schedule, ]
        else:
            return next_schedules

    # Calculates T_target to send to device, when set to proportional mode
    # (in final version, this should be done directly by the device itself)
    # Cycle begins by boiler_on and ends by boiler_off
    def calculateProportional_T_target(self, Tint, Ttarget):
        # Computes target temperatures that ensure that boiler will be on or off
        off_temperature = Tint - (self.coef * 3)
        on_temperature = Tint + (self.coef * 3)
        now =  utils.mydate.now(pytz.UTC)
        # If we are in a cycle                    
        if now < self.prop_end_cycle_date:
            if now > self.prop_start_off_phase_date:
                # Set boiler_off
                return off_temperature
            else:
                # Set boiler_on
                return on_temperature
        # else we are not in a cycle, calculates next cycle
        else:
            # Computes percentage of time to run
            prop_time = ( ( (Ttarget - Tint) / self.prop_band_half_width) + 1.0) / 2
            prop_time = min(max(prop_time, 0.0), 1.0)
            # Translate this percentage in cycle dates
            minutes_on = prop_time * self.prop_duration
            minutes_off = (1-prop_time) * self.prop_duration
            if minutes_on < self.prop_minimum_on_time:
                # Creates a minimum time cycle, during which boiler will be always off
                self.prop_start_off_phase_date = now
                self.prop_end_cycle_date = now + datetime.timedelta(seconds=60*self.prop_minimum_off_time)
                self.save()
                return off_temperature
            if minutes_off < self.prop_minimum_off_time:
                # Creates a full on cycle
                self.prop_end_cycle_date = now + datetime.timedelta(seconds=60*self.prop_duration)
                self.prop_start_off_phase_date = self.prop_end_cycle_date
                self.save()
                return on_temperature
            # Creates the cycle
            self.prop_end_cycle_date = now + datetime.timedelta(seconds=60*self.prop_duration)
            self.prop_start_off_phase_date = now + datetime.timedelta(seconds=60*minutes_on)
            self.save()
            return on_temperature
            
    def __unicode__(self):
        return '%s,%f' % (self.thermostat.name, self.coef)
        

class SavingHistory(models.Model):
    startDate = models.DateTimeField()
    endDate = models.DateTimeField()
    saving = models.FloatField(null=True, default=None)
    thermostat = models.ForeignKey('Thermostat')
    specialSchedule = models.ForeignKey('SpecialSchedule', blank=True, null=True, related_name='saving_history') # can be None  

    def __unicode__(self):
        return '%s,%s,%s' % (self.startDate, self.endDate, self.thermostat.name)
        
    
class SpecialSchedule(models.Model):
    startDate = models.DateTimeField() 
    endDate = models.DateTimeField()
    priority = models.IntegerField()
    thermostat = models.ForeignKey('Thermostat')
    temperatureMode = models.ForeignKey('TemperatureMode')
    savingProposal = models.ForeignKey('SavingProposal', null= True, blank=True, default=None)
    removed = models.BooleanField(default=False)    # SpecialSchedules must not be deleted. We flag them as "removed" instead.

    def __unicode__(self):
        return '%s,%s,%s,%s,%s' % (self.startDate, self.endDate, self.thermostat.name, self.removed, self.temperatureMode.name)

    
class SavingProposal(models.Model):
    SCHEDULE = 'SCHE'
    CAMPAIGN = 'CAMP'
    WEEK = 'WEEK'
    ACTION = 'ACTI'
    
    TYPE_CHOICES = (
        (SCHEDULE, 'Consigne exceptionnelle'),
        (WEEK, 'Semaine type'),
        (CAMPAIGN, 'Campagne') ,
        (ACTION, 'Action')       
    )
    type = models.CharField(max_length=4,
                          choices=TYPE_CHOICES,
                          default=SCHEDULE)

    parameter = models.CharField(max_length=100, default='', null=True, blank=True)    

    # Parameters syntax
    # For SCHEDULE type: 2015-02-10|10:15|2015-02-12|20:30
    # For ACTION type: night_temp_minus_one
    
    messageWhenAccepted = models.CharField(max_length=100, default='', null=True, blank=True)    
    
    PROPOSED = 'PROP'
    APPLIED = 'APPL'
    DISMISSED = 'DISM'
    CANCELED = 'CANC'
    EXPIRED = 'EXPI'
    STATUS_CHOICES = (
        (PROPOSED, 'Proposée'),
        (APPLIED, 'Appliquée'),
        (DISMISSED, 'Refusée'),
        (CANCELED, 'Annulée'),
        (EXPIRED, 'Expirée')
    )
    status = models.CharField(max_length=4,
                          choices=STATUS_CHOICES,
                          default=PROPOSED)

    startValidityPeriod = models.DateTimeField()
    endValidityPeriod = models.DateTimeField()
    title = models.CharField(max_length=100)
    content = models.CharField(max_length=1000)
    amount = models.FloatField()
    thermostat = models.ForeignKey('Thermostat')

    def __unicode__(self):
        return '%s,%s,%s,%s,%s,%s' % (self.status, self.title, self.thermostat.name, self.startValidityPeriod, self.endValidityPeriod, self.type)

    
    def dismiss(self):
        self.status = self.DISMISSED
        self.save()
    
    ##
    # Method to call when applying a saving proposal, if the saving type is ACTION    
    def applySaving(self):
        if self.parameter == "night_temp_minus_one" :
            # Get night temperature mode
            night_tm = self.thermostat.temperaturemode_set.get(internal_code = "NIGH")
            night_tm.temperature -= 1
            night_tm.save()
        # Set status to APPLIED
        self.status = self.APPLIED
        self.save()
    
class WeekSchedule(models.Model):
    thermostat = models.OneToOneField('Thermostat', primary_key=True)
    
    ##
    # Récupère la température applicable à la date de maintenant dans un programme de type WEEK
    # (retourne récursivement en arrière jusqu'à trouver une température applicable)
    def get_last_week_temp(self, now):
        return self.__get_last_week_temp(now, 0)
        
    def __get_last_week_temp(self, now, nb_recursions):
        # Récupère le jour de la semaine
        day_now = now.isoweekday()
        # Récupère la liste des changements de consigne du jour
        try:            
            jour_type = self.weekschedulemarker_set.filter(isoWeekDay = day_now)
        except:
            # Aucun programme défini pour ce jour de la semaine
            jour_type = []            
        # Initialise le résultat
        resultat = {}
        resultat['heure'] = datetime.time(0,0)
        resultat['ok'] = False
        for elt in jour_type:
            # logger.debug("HOUR: %d, MINUTE: %d, daynow: %s" % (elt.hour, elt.minute, day_now))            
            heure_consigne = datetime.time(elt.hour, elt.minute)  
            if (heure_consigne <= now.timetz()):
                # Si on a trouvé une consigne antérieure à l'instant présent
                if (resultat['heure'] <= heure_consigne):
                    # Si on a trouvé une consigne plus récente
                    resultat['ok'] = True
                    resultat['heure'] = heure_consigne
                    resultat['temperatureMode'] = elt.temperatureMode
        
        if resultat['ok']:
            return resultat['temperatureMode']
        else:
            # Incrémente le nombre de récursions et vérifie si on n'a pas déjà fait le tour de la semaine (ne devrait pas arriver, sauf en cas de programme WEEK vide dans la bdd)
            nb_recursions += 1
            if (nb_recursions > 8):
                # Si il n'y a aucun marker défini dans la semaine type, on renvoit le mode confort par défaut
                return self.thermostat.temperaturemode_set.get(internal_code = "COMF")
            else:
                # Passe au jour précédent
                now = now - datetime.timedelta(days=1)      # Retire un jour
                now = datetime.datetime.combine(now.date(), datetime.time(23, 59))    # Récupère la date et passe à 23h59
                # Lance la récursion
                return self.__get_last_week_temp(now, nb_recursions)

    ##
    # Récupère les prochaines températures applicables pour le jour en cours et le jour suivant
    # (récursif jour en cours puis jour suivant : jour_a_traiter = 0 pour le jour en cours, jour_a_traiter = 1 pour le jour suivant)
    # return [(temperature, date_application), ...]    
    def get_next_24h_change(self, mydate):
        return self.__get_next_24h_change(mydate, 0)
    
    def __get_next_24h_change(self, mydate, jour_a_traiter):
        # Récupère le jour de la semaine
        day_now = mydate.isoweekday()
        # Récupère la liste des changements de consigne du jour
        try:
            jour_type = self.weekschedulemarker_set.filter(isoWeekDay = day_now)
        except:
            # Aucun programme défini pour ce jour de la semaine            
            jour_type = []
        # Initialise le résultat
        resultat = []
        tz = pytz.timezone(self.thermostat.timezone)    # TODO à optimiser (passer timezone en paramètre plutôt que de refaire la requête à chaque fois)        
        # Parcourt la liste des changements de consigne du jour
        for elt in jour_type:
            heure_consigne = datetime.time(hour=elt.hour, minute=elt.minute)  
            if ( (heure_consigne > mydate.timetz()) or (jour_a_traiter == 1) ):
                # Si on a trouvé une consigne postérieure à l'instant présent, ou si on est au jour suivant (jour entier à prendre en compte dans ce cas)
                # Transforme le thermpoint en température
                temperatureMode = elt.temperatureMode
                datetime_application_unaware = datetime.datetime.combine(mydate.date(), heure_consigne)
                datetime_application = tz.localize(datetime_application_unaware)
                resultat.append({'temperatureMode': temperatureMode, 'datetime_application': datetime_application})

        if (jour_a_traiter == 1):
            # Si on est au deuxième jour, renvoie le résultat
            return resultat
        else:
            # Si on est au premier jour, poursuit récursivement vers le deuxième jour
            # Passe au jour suivant
            second_jour = mydate + datetime.timedelta(days=1)      # Ajoute un jour
            # Lance la récursion
            resultat = resultat + self.__get_next_24h_change(second_jour, 1)
            # Retourne le résultat
            return resultat
        
    def __unicode__(self):
        return '%s' % (self.thermostat.name)
    
    
    
class WeekScheduleMarker(models.Model):
    # isoWeekDay is an integer in [1, 7], monday is 1
    isoWeekDay = models.IntegerField()
    hour = models.IntegerField()
    minute = models.IntegerField()
    weekSchedule = models.ForeignKey('WeekSchedule')    
    temperatureMode = models.ForeignKey('TemperatureMode')
    
    def __unicode__(self):
        dayOfWeeks = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        return '%s, %s, %d, %d' % (self.weekSchedule.thermostat.name, dayOfWeeks[self.isoWeekDay - 1], self.hour, self.minute)

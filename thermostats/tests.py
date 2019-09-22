from django.test import TestCase
from django.contrib.auth.models import User

from thermostats.models import Thermostat, WeekSchedule, TemperatureMode, WeekScheduleMarker, SpecialSchedule, ControlParameters
from rest_api.views import DeviceStatus
import datetime
import pytz
import mock

class ThermostatBehaviourTests(TestCase):

    ##
    # Creates a user, temperature_modes, a thermostat and and empty week schedule
    #
    def setUp(self):
        self.tz_str = "Europe/Paris"
        date_creation = datetime.datetime(2015, 1, 1, 11, 30, 00, tzinfo = pytz.UTC)
        self.user = User.objects.create_user(username='jacob', email='jacob@free.fr', password='top_secret')
        self.user.save()        
        self.thermostat = Thermostat(createdOn=date_creation, name="TestThermostat", owner=self.user, timezone=self.tz_str, startSavingPeriod=date_creation, uid="testuid", apiKey="testapikey")
        self.thermostat.save()
        self.week_schedule = WeekSchedule(thermostat = self.thermostat)
        self.week_schedule.save()
        self.control_parameters = ControlParameters(thermostat = self.thermostat, coef = 0.3)
        self.control_parameters.save()
        self.temperature_mode_comfort = TemperatureMode(internal_code="COMF", name="Confort", temperature=21.0, thermostat=self.thermostat)
        self.temperature_mode_comfort.save()        
        self.temperature_mode_away = TemperatureMode(internal_code="AWAY", name="Absent", temperature=14.0, thermostat=self.thermostat)
        self.temperature_mode_away.save()
        self.temperature_mode_night = TemperatureMode(internal_code="NIGH", name="Nuit", temperature=19.0, thermostat=self.thermostat)
        self.temperature_mode_night.save()         

    # Mock enables to override a method only for tests purpose
    # Here, we will override the "now" method, in order to choose our test datetimes
    @mock.patch('thermostats.utils.mydate.now')    
    def test_sandbox(self, now_mock):
        """
        first test, not necessary, but written for tests purpose
        """
        now_mock.return_value = datetime.datetime(2015, 1, 1, 12, 00, 00, tzinfo = pytz.UTC)
        future_date = datetime.datetime(2015, 1, 1, 12, 30, 00, tzinfo = pytz.UTC)
        old_date = datetime.datetime(2015, 1, 1, 11, 30, 00, tzinfo = pytz.UTC)
        thermostat = Thermostat(createdOn=datetime.datetime.now, name="TestThermostat", timezone="Europe/Paris", startSavingPeriod=datetime.datetime.now)
        self.assertEqual(old_date < thermostat.now() < future_date, True)

    @mock.patch('thermostats.utils.mydate.now')
    def test_get_raw_schedule_for_week_schedule_with_no_marker(self, now_mock):
        """
        if we have no marker in week schedule, get_raw_schedule should return the temperature mode comfort
        """

        # Check that we get the temperature_mode comfort
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 7, 8, 30, 00))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_comfort)

    @mock.patch('thermostats.utils.mydate.now')
    def test_get_raw_schedule_for_week_schedule_with_only_one_marker(self, now_mock):
        """
        if we have only one marker in week schedule, get_raw_schedule should return the temperature mode of this marker
        for any day in the week
        """

        # Create a unique week_schedule_marker on Wednesday
        week_schedule_marker = WeekScheduleMarker(isoWeekDay=3, hour=11, minute=30, weekSchedule=self.week_schedule, temperatureMode=self.temperature_mode_away)
        week_schedule_marker.save()        

        # Check that we get the temperature_mode away for any hour during the day on Wednedsday (7 Jan 2015 is Wednesday)
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 7, 8, 30, 00))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_away)
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 7, 13, 30, 00))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_away)
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 7, 23, 59, 30))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_away)

        # Check that we get the temperature_mode away for any day, before and after Wednesday
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 6, 8, 30, 00))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_away)
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 8, 8, 30, 00))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_away)

    @mock.patch('thermostats.utils.mydate.now')
    def test_get_raw_schedule_for_week_schedule_with_several_markers(self, now_mock):
        """
        test the global behaviour of week_schedule
        """
        # Create markers in the week schedule
        # Tuesday at 8h30 local time, comfort mode
        week_schedule_marker = WeekScheduleMarker(isoWeekDay=2, hour=8, minute=30, weekSchedule=self.week_schedule, temperatureMode=self.temperature_mode_comfort)
        week_schedule_marker.save()
        # Tuesday at 9h30 local time, away mode
        week_schedule_marker = WeekScheduleMarker(isoWeekDay=2, hour=9, minute=30, weekSchedule=self.week_schedule, temperatureMode=self.temperature_mode_away)
        week_schedule_marker.save()
        # Tuesday at 23h59 local time, night mode
        week_schedule_marker = WeekScheduleMarker(isoWeekDay=2, hour=23, minute=59, weekSchedule=self.week_schedule, temperatureMode=self.temperature_mode_night)
        week_schedule_marker.save()
        # Friday at 9h30 local time, away mode
        week_schedule_marker = WeekScheduleMarker(isoWeekDay=5, hour=9, minute=30, weekSchedule=self.week_schedule, temperatureMode=self.temperature_mode_away)
        week_schedule_marker.save()

        # TESTS for winter time (in January)
        
        # Monday should be away mode at anytime
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 5, 23, 59, 59))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_away)
        
        # Tuesday 0h00 should be away mode
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 6, 0, 0, 0))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_away)
        
        # Tuesday 8h30 should be comfort mode
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 6, 8, 30, 0))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_comfort)
        # Next change should be in 60 minutes and be away mode
        self.assertEqual(self.thermostat.get_raw_schedule()[1]['minutes'], 60)
        self.assertEqual(self.thermostat.get_raw_schedule()[1]['temperatureMode'], self.temperature_mode_away)

        # Tuesday 9h29:59 should be comfort mode
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 6, 9, 29, 59))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_comfort)

        # Tuesday 10h00 should be away mode
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 6, 10, 0, 0))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_away)

        # Wednesday 0h00 should be night mode
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 7, 0, 0, 0))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_night)
        
        # Friday 9h29:59 should be night mode
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 9, 9, 29, 59))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_night)
        
        # Friday 9h30:00 should be away mode
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 9, 9, 30, 00))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_away)
        
        # TESTS for summer time (in July)
        
        # Tuesday 8h30 should be comfort mode
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 7, 14, 8, 30, 0))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_comfort)

        # Tuesday 9h29:59 should be comfort mode
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 7, 14, 9, 29, 59))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_comfort)

        # Tuesday 10h00 should be away mode
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 7, 14, 10, 0, 0))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_away)
        
    @mock.patch('thermostats.utils.mydate.now')
    def test_get_special_schedule(self, now_mock):
        """
        if we have a special_schedule, get_raw_schedule should return the weekSchedule temperature mode before and after this
        special_schedule, and the special_schedule temperature during this special_schedule
        """

        # Create a unique week_schedule_marker on Wednesday, away mode
        week_schedule_marker = WeekScheduleMarker(isoWeekDay=3, hour=11, minute=30, weekSchedule=self.week_schedule, temperatureMode=self.temperature_mode_away)
        week_schedule_marker.save()
        
        # Create a special schedule starting on Jan 7 at 10:00, ending on Jan 8 at 18:00 local time, comfort mode
        startDate = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 7, 10, 00, 00))
        endDate   = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 8, 18, 00, 00))
        special_schedule = SpecialSchedule(startDate=startDate, endDate=endDate, priority=10, thermostat=self.thermostat, temperatureMode=self.temperature_mode_comfort)
        special_schedule.save()

        # Check that we get the temperature_mode away before and after the specialSchedule
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 7, 9, 59, 59))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_away)
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 8, 18, 00, 00))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_away)

        # Check that we get the temperature_mode comfort between startDate and endDate of the specialSchedule
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 7, 10, 00, 00))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_comfort)
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 8, 17, 59, 59))
        self.assertEqual(self.thermostat.get_raw_schedule()[0]['temperatureMode'], self.temperature_mode_comfort)
        
    @mock.patch('thermostats.utils.mydate.now')
    def test_post_device_status(self, now_mock):
        """
        test of post device status
        we create one marker (away mode)
        we post a measured temp
        we check that the response contains away mode
        we check that measured temp has been recorded
        """

        # Initialise the value of temperature to record
        my_temperature = 25.2

        # Create a unique week_schedule_marker on Wednesday
        week_schedule_marker = WeekScheduleMarker(isoWeekDay=3, hour=11, minute=30, weekSchedule=self.week_schedule, temperatureMode=self.temperature_mode_away)
        week_schedule_marker.save()  

        # Tell what time it is        
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 5, 23, 59, 59))

        # Post a new measured temp
        data = {
            "uid" : "testuid",
            "apikey" : "testapikey",
            "temperature" : my_temperature,
            "boilerOn" : True,
            "manual" : False,
            "tcons" : 20.5
        }
        request = lambda:x
        request.data = data
        mt = DeviceStatus()
        response = DeviceStatus.post(mt, request)
        
        # Check that the target temperature in the response is equal to the away temperature
        self.assertEqual(response.data['target_temp'], self.temperature_mode_away.temperature)
        # Check that the temperature recorded is correct
        last_temp_recorded = self.thermostat.measuredtemp_set.last()
        self.assertEqual(last_temp_recorded.temperature, my_temperature)
        
    @mock.patch('thermostats.utils.mydate.now')
    def test_post_device_status_proportional(self, now_mock):
        """
        test of post device status when proportional mode is on
        we create one marker (away mode)
        we post a measured temp
        we check that the response contains off_temperature (Tint - 3*coef hysteresis)
        we check that measured temp has been recorded
        """
        # Set proportional mode on
        self.control_parameters.prop_mode = True
        self.control_parameters.save()

        # Initialise the value of temperature to record
        my_temperature = 25.2

        # Create a unique week_schedule_marker on Wednesday
        week_schedule_marker = WeekScheduleMarker(isoWeekDay=3, hour=11, minute=30, weekSchedule=self.week_schedule, temperatureMode=self.temperature_mode_away)
        week_schedule_marker.save()  

        # Tell what time it is        
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 5, 23, 59, 59))

        # Post a new measured temp
        data = {
            "uid" : "testuid",
            "apikey" : "testapikey",
            "temperature" : my_temperature,
            "boilerOn" : True,
            "manual" : False,
            "tcons" : 20.5
        }
        request = lambda:x
        request.data = data
        mt = DeviceStatus()
        response = DeviceStatus.post(mt, request)
        
        # Check that the target temperature in the response is equal to the away temperature
        self.assertEqual(response.data['target_temp'], my_temperature - 3*self.control_parameters.coef)
        # Check that the temperature recorded is correct
        last_temp_recorded = self.thermostat.measuredtemp_set.last()
        self.assertEqual(last_temp_recorded.temperature, my_temperature)
        self.assertEqual(last_temp_recorded.userRequestedTemperature, self.temperature_mode_away.temperature)
        
    @mock.patch('thermostats.utils.mydate.now')
    def test_proportional_command(self, now_mock):
        """
        Tests proportional command behaviour
        """

        # Create a unique week_schedule_marker on Wednesday
        week_schedule_marker = WeekScheduleMarker(isoWeekDay=3, hour=11, minute=30, weekSchedule=self.week_schedule, temperatureMode=self.temperature_mode_away)
        week_schedule_marker.save()
        
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 00, 00))
        Tint = 19.5
        Ttarget = 21
        device_target = self.thermostat.controlparameters.calculateProportional_T_target(Tint, Ttarget)
        # Checks that cycle is always on, and that it will end in 20 minutes
        self.assertEqual(self.thermostat.controlparameters.prop_start_off_phase_date, pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 20, 00)))
        self.assertEqual(self.thermostat.controlparameters.prop_end_cycle_date, pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 20, 00)))
        self.assertEqual(device_target, Tint + 3*self.control_parameters.coef) # Tint + 3*hysteresis coef
        # Checks that cycle is still on, and that end of cycle has not changed
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 19, 55))
        Tint = 22.5
        Ttarget = 21
        device_target = self.thermostat.controlparameters.calculateProportional_T_target(Tint, Ttarget)                
        self.assertEqual(self.thermostat.controlparameters.prop_start_off_phase_date, pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 20, 00)))
        self.assertEqual(self.thermostat.controlparameters.prop_end_cycle_date, pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 20, 00)))
        self.assertEqual(device_target, Tint + 3*self.control_parameters.coef) # Tint + 3*hysteresis coef
        
        # Checks a 50% cycle
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 21, 00))
        Tint = 22.0
        Ttarget = 22.0
        device_target = self.thermostat.controlparameters.calculateProportional_T_target(Tint, Ttarget)                
        self.assertEqual(self.thermostat.controlparameters.prop_start_off_phase_date, pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 31, 00)))
        self.assertEqual(self.thermostat.controlparameters.prop_end_cycle_date, pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 41, 00)))
        self.assertEqual(device_target, Tint + 3*self.control_parameters.coef) # Tint + 3*hysteresis coef
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 30, 55))
        device_target = self.thermostat.controlparameters.calculateProportional_T_target(Tint, Ttarget)                
        self.assertEqual(self.thermostat.controlparameters.prop_start_off_phase_date, pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 31, 00)))
        self.assertEqual(self.thermostat.controlparameters.prop_end_cycle_date, pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 41, 00)))
        self.assertEqual(device_target, Tint + 3*self.control_parameters.coef) # Tint + 3*hysteresis coef
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 31, 01))
        device_target = self.thermostat.controlparameters.calculateProportional_T_target(Tint, Ttarget)                
        self.assertEqual(self.thermostat.controlparameters.prop_start_off_phase_date, pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 31, 00)))
        self.assertEqual(self.thermostat.controlparameters.prop_end_cycle_date, pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 41, 00)))
        self.assertEqual(device_target, Tint - 3*self.control_parameters.coef) # Tint - 3*hysteresis coef
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 40, 55))
        device_target = self.thermostat.controlparameters.calculateProportional_T_target(Tint, Ttarget)                
        self.assertEqual(self.thermostat.controlparameters.prop_start_off_phase_date, pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 31, 00)))
        self.assertEqual(self.thermostat.controlparameters.prop_end_cycle_date, pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 41, 00)))
        self.assertEqual(device_target, Tint - 3*self.control_parameters.coef) # Tint - 3*hysteresis coef        
        
    @mock.patch('thermostats.utils.mydate.now')
    def test_derivative_algorithm(self, now_mock):
        """
        Tests derivative algorithm behaviour
        """

        # Create a unique week_schedule_marker on Wednesday
        week_schedule_marker = WeekScheduleMarker(isoWeekDay=3, hour=11, minute=30, weekSchedule=self.week_schedule, temperatureMode=self.temperature_mode_away)
        week_schedule_marker.save()
        
        # Set derivative_coeff
        self.control_parameters.deriv_coef = 60
        self.control_parameters.save()

        # Set fake now date
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 00, 00))        
        # Post a new measured temp
        data = {
            "uid" : "testuid",
            "apikey" : "testapikey",
            "temperature" : 21.0,
            "boilerOn" : True,
            "manual" : False,
            "tcons" : 20.5
        }
        request = lambda:x
        request.data = data
        mt = DeviceStatus()
        response = DeviceStatus.post(mt, request)

        # Set fake now date
        now_mock.return_value = pytz.timezone(self.tz_str).localize(datetime.datetime(2015, 1, 10, 10, 45, 00))        
        
        Tint = 20.25
        deriv_offset = self.thermostat.controlparameters.derivativeOffset(Tint)
        # Checks that deriv_offset is correct        
        self.assertEqual(deriv_offset, -1.0)
        
        
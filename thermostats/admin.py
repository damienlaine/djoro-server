from django.contrib import admin
from thermostats.models import Thermostat, TemperatureMode, MeasuredTemp, WeekSchedule, WeekScheduleMarker, SpecialSchedule, BuildingParameters, SavingHistory, ControlParameters, SavingProposal, ProfessionalUser

class TemperatureModeInline(admin.TabularInline):
    model = TemperatureMode
    extra = 0

class SavingProposalInline(admin.TabularInline):
    model = SavingProposal
    extra = 0

class ThermostatAdmin(admin.ModelAdmin):
    inlines = [SavingProposalInline, TemperatureModeInline]    

admin.site.register(Thermostat, ThermostatAdmin)
admin.site.register(MeasuredTemp)
admin.site.register(WeekSchedule)
admin.site.register(WeekScheduleMarker)
admin.site.register(SpecialSchedule)
admin.site.register(BuildingParameters)
admin.site.register(SavingHistory)
admin.site.register(ControlParameters)
admin.site.register(SavingProposal)
admin.site.register(ProfessionalUser)
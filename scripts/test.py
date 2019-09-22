# scripts/test.py
from thermostats.models import Thermostat

def run():
    # Test real_money_saved_calc
    thermostat = Thermostat.objects.get(pk=1)
    print "Savings pour le thermostat : ", thermostat.name
    print "Montant calcule : ", thermostat.real_money_saved_calc()

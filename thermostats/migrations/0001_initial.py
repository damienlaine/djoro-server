# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MeasuredTemp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('measuredOn', models.DateTimeField(auto_now_add=True)),
                ('temperature', models.FloatField(default=-99.0)),
                ('manual', models.BooleanField(default=False)),
                ('targetTemperature', models.FloatField(default=-99.0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SavingHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('startDate', models.DateTimeField()),
                ('endDate', models.DateTimeField()),
                ('saving', models.FloatField(default=None, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SavingProposal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(default=b'CAMP', max_length=4, choices=[(b'SCHE', b'Programmation'), (b'CAMP', b'Campagne')])),
                ('status', models.CharField(default=b'PROP', max_length=4, choices=[(b'PROP', b'Propos\xc3\xa9e'), (b'APPL', b'Appliqu\xc3\xa9e'), (b'DISM', b'Annul\xc3\xa9e'), (b'EXPI', b'Expir\xc3\xa9e')])),
                ('startValidityPeriod', models.DateTimeField()),
                ('endValidityPeriod', models.DateTimeField()),
                ('title', models.CharField(max_length=100)),
                ('content', models.CharField(max_length=1000)),
                ('amount', models.FloatField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SetPointHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('createdOn', models.DateTimeField(auto_now_add=True)),
                ('temperature', models.FloatField()),
                ('modeName', models.CharField(max_length=100)),
                ('modeInternalCode', models.CharField(max_length=4)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SpecialSchedule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('startDate', models.DateTimeField()),
                ('endDate', models.DateTimeField()),
                ('priority', models.IntegerField()),
                ('removed', models.BooleanField(default=False)),
                ('savingProposal', models.ForeignKey(default=None, blank=True, to='thermostats.SavingProposal', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TemperatureMode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('internal_code', models.CharField(default=b'CUST', max_length=4, choices=[(b'COMF', b'Confort'), (b'AWAY', b'Absent'), (b'NIGH', b'Nuit'), (b'CUST', b'Custom')])),
                ('name', models.CharField(default=b'Temp\xc3\xa9rature Utilisateur', max_length=100)),
                ('temperature', models.FloatField()),
                ('removable', models.BooleanField(default=True)),
                ('removed', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Thermostat',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('createdOn', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(default=b'', max_length=100, blank=True)),
                ('timezone', models.CharField(default=b'Europe/Paris', max_length=100)),
                ('address', models.CharField(default=b'', max_length=1024, blank=True)),
                ('uid', models.CharField(default=b'', max_length=128, blank=True)),
                ('apiKey', models.CharField(default=b'', max_length=128, blank=True)),
                ('startSavingPeriod', models.DateTimeField()),
                ('totalSavingForPeriod', models.FloatField(default=0.0)),
                ('boilerOn', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ('createdOn',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ControlParameters',
            fields=[
                ('coef', models.FloatField(default=0.1)),
                ('thermostat', models.OneToOneField(primary_key=True, serialize=False, to='thermostats.Thermostat')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BuildingParameters',
            fields=[
                ('annualEnergyBill', models.FloatField()),
                ('annualSubscriptionAmount', models.FloatField()),
                ('boilerType', models.CharField(default=b'GAS', max_length=4, choices=[(b'GAS', b'Gaz'), (b'OIL', b'Fuel'), (b'ELEC', b'Electrique')])),
                ('dju', models.FloatField()),
                ('thermostat', models.OneToOneField(related_name='building_parameters', primary_key=True, serialize=False, to='thermostats.Thermostat')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='WeekSchedule',
            fields=[
                ('thermostat', models.OneToOneField(primary_key=True, serialize=False, to='thermostats.Thermostat')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='WeekScheduleMarker',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('isoWeekDay', models.IntegerField()),
                ('hour', models.IntegerField()),
                ('minute', models.IntegerField()),
                ('temperatureMode', models.ForeignKey(to='thermostats.TemperatureMode')),
                ('weekSchedule', models.ForeignKey(to='thermostats.WeekSchedule')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='thermostat',
            name='owner',
            field=models.ForeignKey(related_name='thermostats', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='temperaturemode',
            name='thermostat',
            field=models.ForeignKey(to='thermostats.Thermostat'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='specialschedule',
            name='temperatureMode',
            field=models.ForeignKey(to='thermostats.TemperatureMode'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='specialschedule',
            name='thermostat',
            field=models.ForeignKey(to='thermostats.Thermostat'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='setpointhistory',
            name='thermostat',
            field=models.ForeignKey(related_name='set_point_history', to='thermostats.Thermostat'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='savingproposal',
            name='thermostat',
            field=models.ForeignKey(related_name='saving_proposal', to='thermostats.Thermostat'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='savinghistory',
            name='specialSchedule',
            field=models.ForeignKey(related_name='saving_history', blank=True, to='thermostats.SpecialSchedule', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='savinghistory',
            name='thermostat',
            field=models.ForeignKey(to='thermostats.Thermostat'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='measuredtemp',
            name='thermostat',
            field=models.ForeignKey(to='thermostats.Thermostat'),
            preserve_default=True,
        ),
    ]

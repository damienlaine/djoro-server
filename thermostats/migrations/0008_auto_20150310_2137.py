# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('thermostats', '0007_auto_20150224_2305'),
    ]

    operations = [
        migrations.AddField(
            model_name='controlparameters',
            name='deriv_coef',
            field=models.FloatField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='controlparameters',
            name='prop_band_half_width',
            field=models.FloatField(default=1),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='controlparameters',
            name='prop_duration',
            field=models.FloatField(default=20),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='controlparameters',
            name='prop_end_cycle_date',
            field=models.DateTimeField(default=datetime.datetime(2010, 1, 1, 0, 0, tzinfo=utc)),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='controlparameters',
            name='prop_minimum_off_time',
            field=models.FloatField(default=3),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='controlparameters',
            name='prop_minimum_on_time',
            field=models.FloatField(default=7),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='controlparameters',
            name='prop_mode',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='controlparameters',
            name='prop_start_off_phase_date',
            field=models.DateTimeField(default=datetime.datetime(2010, 1, 1, 0, 0, tzinfo=utc)),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='measuredtemp',
            name='userRequestedTemperature',
            field=models.FloatField(default=None, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='measuredtemp',
            name='measuredOn',
            field=models.DateTimeField(),
            preserve_default=True,
        ),
    ]

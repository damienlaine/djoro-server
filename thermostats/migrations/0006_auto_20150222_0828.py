# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('thermostats', '0005_auto_20150216_1948'),
    ]

    operations = [
        migrations.AddField(
            model_name='measuredtemp',
            name='T_ext',
            field=models.FloatField(default=None, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='thermostat',
            name='last_Text_date',
            field=models.DateTimeField(default=b'2010-01-01T00:00'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='thermostat',
            name='latitude',
            field=models.CharField(default=b'43.60', max_length=100),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='thermostat',
            name='longitude',
            field=models.CharField(default=b'1.43', max_length=100),
            preserve_default=True,
        ),
    ]

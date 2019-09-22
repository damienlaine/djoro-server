# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('thermostats', '0006_auto_20150222_0828'),
    ]

    operations = [
        migrations.AlterField(
            model_name='thermostat',
            name='last_Text_date',
            field=models.DateTimeField(default=datetime.datetime(2010, 1, 1, 0, 0)),
            preserve_default=True,
        ),
    ]

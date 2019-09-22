# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('thermostats', '0003_auto_20150214_0815'),
    ]

    operations = [
        migrations.AddField(
            model_name='controlparameters',
            name='anticipation_coef',
            field=models.FloatField(default=15),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='controlparameters',
            name='anticipation_exp',
            field=models.FloatField(default=1.5),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='controlparameters',
            name='anticipation_max_hours',
            field=models.FloatField(default=8),
            preserve_default=True,
        ),
    ]

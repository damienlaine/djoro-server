# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('thermostats', '0004_auto_20150216_1600'),
    ]

    operations = [
        migrations.AlterField(
            model_name='controlparameters',
            name='anticipation_coef',
            field=models.FloatField(default=90),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='controlparameters',
            name='anticipation_exp',
            field=models.FloatField(default=1),
            preserve_default=True,
        ),
    ]

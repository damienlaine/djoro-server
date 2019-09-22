# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('thermostats', '0002_auto_20150209_2212'),
    ]

    operations = [
        migrations.AddField(
            model_name='measuredtemp',
            name='boilerOn',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='savingproposal',
            name='messageWhenAccepted',
            field=models.CharField(default=b'', max_length=100, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='savingproposal',
            name='parameter',
            field=models.CharField(default=b'', max_length=100, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='savingproposal',
            name='thermostat',
            field=models.ForeignKey(to='thermostats.Thermostat'),
            preserve_default=True,
        ),
    ]

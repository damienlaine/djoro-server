# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('thermostats', '0008_auto_20150310_2137'),
    ]

    operations = [
        migrations.AddField(
            model_name='thermostat',
            name='last_maintenance_date',
            field=models.DateField(default=datetime.date(2010, 1, 1)),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='savingproposal',
            name='status',
            field=models.CharField(default=b'PROP', max_length=4, choices=[(b'PROP', b'Propos\xc3\xa9e'), (b'APPL', b'Appliqu\xc3\xa9e'), (b'DISM', b'Refus\xc3\xa9e'), (b'CANC', b'Annul\xc3\xa9e'), (b'EXPI', b'Expir\xc3\xa9e')]),
            preserve_default=True,
        ),
    ]

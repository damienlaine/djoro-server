# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('thermostats', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='savingproposal',
            name='messageWhenAccepted',
            field=models.CharField(default=b'', max_length=100),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='savingproposal',
            name='parameter',
            field=models.CharField(default=b'', max_length=100),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='savingproposal',
            name='type',
            field=models.CharField(default=b'SCHE', max_length=4, choices=[(b'SCHE', b'Consigne exceptionnelle'), (b'WEEK', b'Semaine type'), (b'CAMP', b'Campagne'), (b'ACTI', b'Action')]),
            preserve_default=True,
        ),
    ]

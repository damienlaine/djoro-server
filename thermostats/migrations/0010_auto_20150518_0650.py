# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('thermostats', '0009_auto_20150406_1956'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfessionalUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='thermostat',
            name='professionalOwner',
            field=models.ForeignKey(default=None, to='thermostats.ProfessionalUser', null=True),
            preserve_default=True,
        ),
    ]

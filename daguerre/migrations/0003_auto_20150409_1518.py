# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import daguerre.models


class Migration(migrations.Migration):

    dependencies = [
        ('daguerre', '0002_auto_20140904_2006'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adjustedimage',
            name='adjusted',
            field=models.ImageField(max_length=45, upload_to=daguerre.models.upload_to),
        ),
    ]

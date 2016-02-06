# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('daguerre', '0003_auto_20150409_1518'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='adjustedimage',
            index_together=set([('requested', 'storage_path')]),
        ),
    ]

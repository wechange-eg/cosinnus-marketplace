# Generated by Django 2.1.7 on 2019-07-14 15:55

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_marketplace', '0008_auto_20190527_1759'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='settings',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict, blank=True, null=True),
        ),
    ]

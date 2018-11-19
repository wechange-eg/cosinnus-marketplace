# Generated by Django 2.0.9 on 2018-11-16 18:44

from django.db import migrations, models


def set_last_modified(apps, schema_editor):
    Offer = apps.get_model('cosinnus_marketplace', 'Offer')
    Offer.objects.update(last_modified=models.F('created'))


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus_marketplace', '0005_auto_20180926_1357'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='last_modified',
            field=models.DateTimeField(auto_now=True, verbose_name='Last modified'),
        ),
        migrations.RunPython(set_last_modified, migrations.RunPython.noop)
    ]

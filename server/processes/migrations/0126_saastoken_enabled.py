# Generated by Django 2.2.14 on 2020-08-21 06:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0125_auto_20200821_0645'),
    ]

    operations = [
        migrations.AddField(
            model_name='saastoken',
            name='enabled',
            field=models.BooleanField(default=True),
        ),
    ]

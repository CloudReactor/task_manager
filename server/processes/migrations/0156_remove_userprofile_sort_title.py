# Generated by Django 3.2.6 on 2021-08-29 05:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0155_auto_20210824_0628'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='sort_title',
        ),
    ]

# Generated by Django 2.2.12 on 2020-04-19 05:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0104_auto_20200419_0528'),
    ]

    operations = [
        migrations.RenameField(
            model_name='processexecution',
            old_name='command',
            new_name='process_command',
        ),
    ]

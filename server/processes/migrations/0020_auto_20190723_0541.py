# Generated by Django 2.2.2 on 2019-07-23 05:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0019_auto_20190722_0643'),
    ]

    operations = [
        migrations.RenameField(
            model_name='processexecution',
            old_name='host_name',
            new_name='hostname',
        ),
    ]

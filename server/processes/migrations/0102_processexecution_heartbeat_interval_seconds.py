# Generated by Django 2.2.12 on 2020-04-17 21:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0101_auto_20200412_2159'),
    ]

    operations = [
        migrations.AddField(
            model_name='processexecution',
            name='heartbeat_interval_seconds',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]

# Generated by Django 2.2.2 on 2020-02-05 00:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0089_processtype_max_heartbeat_lateness_before_abandonment_seconds'),
    ]

    operations = [
        migrations.RenameField(
            model_name='processtype',
            old_name='max_manual_start_delay_seconds',
            new_name='max_manual_start_delay_before_alert_seconds',
        ),
    ]

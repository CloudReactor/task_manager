# Generated by Django 2.2.2 on 2019-11-12 10:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0058_auto_20191111_0637'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='processexecution',
            name='pagerduty_event_dedup_key',
        ),
        migrations.RemoveField(
            model_name='processexecution',
            name='pagerduty_event_sent_at',
        ),
    ]

# Generated by Django 2.2.2 on 2019-11-12 22:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0063_auto_20191112_2219'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='alertmethod',
            name='pagerduty_event_summary_template',
        ),
        migrations.RemoveField(
            model_name='pagerdutyprofile',
            name='default_event_summary_template',
        ),
    ]

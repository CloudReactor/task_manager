# Generated by Django 2.2.2 on 2019-06-17 06:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0004_auto_20190617_0347'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='processexecution',
            name='pagerduty_event_class_template',
        ),
        migrations.RemoveField(
            model_name='processexecution',
            name='pagerduty_event_component_template',
        ),
        migrations.RemoveField(
            model_name='processexecution',
            name='pagerduty_event_group_template',
        ),
        migrations.RemoveField(
            model_name='processexecution',
            name='pagerduty_event_summary_template',
        ),
    ]

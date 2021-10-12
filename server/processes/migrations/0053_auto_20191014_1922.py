# Generated by Django 2.2.2 on 2019-10-14 19:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0052_workflow_scheduling_run_environment'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflow',
            name='aws_event_target_id',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AddField(
            model_name='workflow',
            name='aws_event_target_rule_name',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AddField(
            model_name='workflow',
            name='aws_scheduled_event_rule_arn',
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AddField(
            model_name='workflow',
            name='aws_scheduled_execution_rule_name',
            field=models.CharField(blank=True, max_length=1000),
        ),
    ]

# Generated by Django 2.2.14 on 2021-01-31 06:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0142_auto_20210131_0621'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskexecution',
            name='api_error_timeout_seconds',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taskexecution',
            name='api_final_update_timeout_seconds',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taskexecution',
            name='api_resume_delay_seconds',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taskexecution',
            name='api_task_execution_creation_conflict_timeout_seconds',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taskexecution',
            name='api_task_execution_creation_error_timeout_seconds',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='taskexecution',
            name='api_task_execution_creation_retry_delay_seconds',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]

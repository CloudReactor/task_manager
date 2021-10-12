# Generated by Django 2.2.2 on 2019-11-10 01:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0056_runenvironment_aws_workflow_starter_access_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflow',
            name='alert_methods',
            field=models.ManyToManyField(blank=True, to='processes.AlertMethod'),
        ),
        migrations.AddField(
            model_name='workflowprocesstypeinstance',
            name='allow_workflow_execution_after_failure',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='workflowprocesstypeinstance',
            name='allow_workflow_execution_after_timeout',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='workflowprocesstypeinstance',
            name='failure_behavior',
            field=models.CharField(choices=[('ignore', 'Ignore'), ('always_fail_workflow', 'Always fail workflow'), ('fail_workflow_if_unhandled', 'Fail workflow if unhandled')], default='fail_workflow_if_unhandled', max_length=50),
        ),
        migrations.AddField(
            model_name='workflowprocesstypeinstance',
            name='timeout_behavior',
            field=models.CharField(choices=[('ignore', 'Ignore'), ('always_timeout_workflow', 'Always timeout workflow'), ('timeout_workflow_if_unhandled', 'Timeout workflow if unhandled')], default='timeout_workflow_if_unhandled', max_length=50),
        ),
        migrations.AddField(
            model_name='workflowprocesstypeinstance',
            name='use_process_type_alert_methods',
            field=models.BooleanField(default=False),
        ),
    ]

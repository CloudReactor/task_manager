# Generated by Django 2.2.2 on 2019-10-29 09:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0053_auto_20191014_1922'),
    ]

    operations = [
        migrations.AddField(
            model_name='processexecution',
            name='stop_reason',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='processtype',
            name='latest_process_execution',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='processes.ProcessExecution'),
        ),
        migrations.AlterField(
            model_name='workflow',
            name='latest_workflow_execution',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='processes.WorkflowExecution'),
        ),
    ]

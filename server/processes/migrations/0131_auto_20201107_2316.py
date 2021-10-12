# Generated by Django 2.2.14 on 2020-11-07 23:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0130_pagerdutyprofile_run_environment'),
    ]

    operations = [
        migrations.AddField(
            model_name='workflow',
            name='run_environment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='processes.RunEnvironment'),
        ),
        migrations.AlterField(
            model_name='workflowprocesstypeinstance',
            name='workflow',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workflow_task_instances', to='processes.Workflow'),
        ),
    ]

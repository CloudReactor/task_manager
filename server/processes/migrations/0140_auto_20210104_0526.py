# Generated by Django 2.2.14 on 2021-01-04 05:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0139_model_renames'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='WorkflowProcessTypeInstance',
            new_name='WorkflowTaskInstance',
        ),
        migrations.RenameModel(
            old_name='WorkflowProcessTypeInstanceExecution',
            new_name='WorkflowTaskInstanceExecution',
        ),
        migrations.AlterModelTable(
            name='workflowtaskinstance',
            table='processes_workflowprocesstypeinstance',
        ),
        migrations.AlterModelTable(
            name='workflowtaskinstanceexecution',
            table='processes_workflowprocesstypeinstanceexecution',
        ),
    ]

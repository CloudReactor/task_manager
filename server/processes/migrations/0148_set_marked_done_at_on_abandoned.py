# Generated by Django 2.2.19 on 2021-04-02 07:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0147_task_execution_method_type'),
    ]

    operations = [
        migrations.RunSQL(
            [("""
UPDATE processes_processexecution
SET marked_done_at = CURRENT_TIMESTAMP
WHERE (marked_done_at IS NULL)
AND (status IN (4, 5, 8, 10));
"""
            )]
        ),
    ]

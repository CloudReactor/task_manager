"""Create composite index on `processes_event(task_execution_id, event_at)`.

This migration creates a single index to accelerate queries that filter or
order events by `task_execution_id` and `event_at` on the single-table
`processes_event` layout used by the project.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0218_create_event_taskid_eventat_index'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS processes_event_task_exec_event_at_idx "
                "ON processes_event (task_execution_id, event_at);"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS processes_event_task_exec_event_at_idx;"
            ),
        ),
    ]

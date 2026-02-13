"""Create composite index on `processes_event(workflow_id, event_at)`."""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0219_create_event_task_exec_index'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS processes_event_workflow_event_at_idx "
                "ON processes_event (workflow_id, event_at);"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS processes_event_workflow_event_at_idx;"
            ),
        ),
    ]

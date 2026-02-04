"""Create composite index on `processes_event(task_id, event_at)` for STI setup.

This project uses single-table inheritance, so subclass fields (like `task_id`)
live on the `processes_event` table. Create a DB index directly on that table
to support queries ordering/filtering by task and event time.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('processes', '0217_event_processes_e_run_env_8ec567_idx'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS processes_event_task_event_at_idx "
                "ON processes_event (task_id, event_at);"
            ),
            reverse_sql=(
                "DROP INDEX IF EXISTS processes_event_task_event_at_idx;"
            ),
        ),
    ]

# Generated manually on 2026-03-09

from django.db import migrations, models
from django.contrib.postgres.operations import AddIndexConcurrently


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("processes", "0227_remove_delayedprocessstartalert_alert_method_and_more"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="taskexecution",
            index=models.Index(
                fields=["task", "started_at"],
                name="processes_taskexec_task_started_at_idx",
            ),
        ),
    ]

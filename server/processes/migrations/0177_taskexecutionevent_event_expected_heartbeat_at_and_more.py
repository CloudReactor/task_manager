# Generated by Django 4.2.11 on 2024-04-28 09:30

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        (
            "processes",
            "0176_rename_heartbeatdetectionevent_legacyheartbeatdetectionevent_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="TaskExecutionEvent",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("processes.event",),
        ),
        migrations.AddField(
            model_name="event",
            name="expected_heartbeat_at",
            field=models.DateTimeField(default=datetime.datetime.now, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="heartbeat_interval_seconds",
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="last_heartbeat_at",
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="task_execution",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="processes.taskexecution",
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="type",
            field=models.CharField(
                choices=[
                    ("processes.heartbeatdetectionevent", "heartbeat detection event"),
                    ("processes.taskexecutionevent", "task execution event"),
                ],
                db_index=True,
                max_length=255,
            ),
        ),
        migrations.CreateModel(
            name="HeartbeatDetectionEvent",
            fields=[],
            options={
                "ordering": ["detected_at"],
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("processes.taskexecutionevent",),
        ),
    ]

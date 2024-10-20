# Generated by Django 4.2.14 on 2024-08-26 01:34

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import processes.models.alert_send_status
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        (
            "processes",
            "0179_rename_heartbeatdetectionalert_legacyheartbeatdetectionalert_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("attempted_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "send_status",
                    models.IntegerField(
                        blank=True,
                        default=processes.models.alert_send_status.AlertSendStatus[
                            "SENDING"
                        ],
                        null=True,
                    ),
                ),
                ("send_result", models.JSONField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="NotificationDeliveryMethod",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=200)),
                ("description", models.CharField(blank=True, max_length=5000)),
                ("type", models.CharField(choices=[], db_index=True, max_length=255)),
                (
                    "created_by_group",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="auth.group",
                    ),
                ),
                (
                    "created_by_user",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "run_environment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="processes.runenvironment",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="NotificationProfile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=200)),
                ("description", models.CharField(blank=True, max_length=5000)),
                ("enabled", models.BooleanField(default=True)),
                (
                    "created_by_group",
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="auth.group",
                    ),
                ),
                (
                    "created_by_user",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "notification_delivery_methods",
                    models.ManyToManyField(to="processes.notificationdeliverymethod"),
                ),
                (
                    "run_environment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="processes.runenvironment",
                    ),
                ),
            ],
            options={
                "unique_together": {("name", "created_by_group")},
            },
        ),
        migrations.DeleteModel(
            name="HeartbeatDetectionEvent",
        ),
        migrations.CreateModel(
            name="ExecutionStatusChangeEvent",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("processes.event",),
        ),
        migrations.CreateModel(
            name="MissingHeartbeatDetectionEvent",
            fields=[],
            options={
                "ordering": ["detected_at"],
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("processes.taskexecutionevent",),
        ),
        migrations.CreateModel(
            name="WorkflowExecutionEvent",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("processes.event",),
        ),
        migrations.RenameField(
            model_name="event",
            old_name="error_message",
            new_name="error_details_message",
        ),
        migrations.AddField(
            model_name="event",
            name="details",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="error_summary",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="event",
            name="grouping_key",
            field=models.CharField(blank=True, max_length=5000),
        ),
        migrations.AddField(
            model_name="event",
            name="resolved_event",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                to="processes.event",
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="severity",
            field=models.PositiveIntegerField(default=500),
        ),
        migrations.AddField(
            model_name="event",
            name="source",
            field=models.CharField(blank=True, max_length=1000),
        ),
        migrations.AddField(
            model_name="event",
            name="workflow_execution",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="processes.workflowexecution",
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="notification_event_severity_on_failure",
            field=models.PositiveIntegerField(blank=True, default=500, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="notification_event_severity_on_missing_execution",
            field=models.PositiveIntegerField(blank=True, default=500, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="notification_event_severity_on_missing_heartbeat",
            field=models.PositiveIntegerField(blank=True, default=400, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="notification_event_severity_on_service_down",
            field=models.PositiveIntegerField(blank=True, default=500, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="notification_event_severity_on_success",
            field=models.PositiveIntegerField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="notification_event_severity_on_timeout",
            field=models.PositiveIntegerField(blank=True, default=500, null=True),
        ),
        migrations.AddField(
            model_name="workflow",
            name="notification_event_severity_on_failure",
            field=models.PositiveIntegerField(blank=True, default=500, null=True),
        ),
        migrations.AddField(
            model_name="workflow",
            name="notification_event_severity_on_missing_execution",
            field=models.PositiveIntegerField(blank=True, default=500, null=True),
        ),
        migrations.AddField(
            model_name="workflow",
            name="notification_event_severity_on_missing_heartbeat",
            field=models.PositiveIntegerField(blank=True, default=400, null=True),
        ),
        migrations.AddField(
            model_name="workflow",
            name="notification_event_severity_on_service_down",
            field=models.PositiveIntegerField(blank=True, default=500, null=True),
        ),
        migrations.AddField(
            model_name="workflow",
            name="notification_event_severity_on_success",
            field=models.PositiveIntegerField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name="workflow",
            name="notification_event_severity_on_timeout",
            field=models.PositiveIntegerField(blank=True, default=500, null=True),
        ),
        migrations.AddField(
            model_name="workflowexecution",
            name="error_details",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="workflowexecution",
            name="input_value",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="workflowexecution",
            name="marked_outdated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="workflowexecution",
            name="other_instance_metadata",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="workflowexecution",
            name="other_runtime_metadata",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="workflowexecution",
            name="output_value",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="workflowtaskinstance",
            name="use_task_notification_profiles",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="event",
            name="type",
            field=models.CharField(
                choices=[
                    (
                        "processes.executionstatuschangeevent",
                        "execution status change event",
                    ),
                    (
                        "processes.missingheartbeatdetectionevent",
                        "missing heartbeat detection event",
                    ),
                    ("processes.taskexecutionevent", "task execution event"),
                    (
                        "processes.taskexecutionstatuschangeevent",
                        "task execution status change event",
                    ),
                    ("processes.workflowexecutionevent", "workflow execution event"),
                    (
                        "processes.workflowexecutionstatuschangeevent",
                        "workflow execution status change event",
                    ),
                ],
                db_index=True,
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="workflowexecution",
            name="failed_attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="workflowexecution",
            name="timed_out_attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="notification",
            name="event",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="processes.event"
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="notification_delivery_method",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="processes.notificationdeliverymethod",
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="notification_profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="processes.notificationprofile",
            ),
        ),
        migrations.CreateModel(
            name="WorkflowExecutionStatusChangeEvent",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=(
                "processes.executionstatuschangeevent",
                "processes.workflowexecutionevent",
            ),
        ),
        migrations.AddField(
            model_name="runenvironment",
            name="notification_profiles",
            field=models.ManyToManyField(to="processes.notificationprofile"),
        ),
        migrations.AddField(
            model_name="task",
            name="notification_profiles",
            field=models.ManyToManyField(to="processes.notificationprofile"),
        ),
        migrations.AddField(
            model_name="workflow",
            name="notification_profiles",
            field=models.ManyToManyField(to="processes.notificationprofile"),
        ),
    ]

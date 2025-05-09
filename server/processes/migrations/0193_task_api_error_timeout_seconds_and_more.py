# Generated by Django 4.2.18 on 2025-03-21 06:16

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("processes", "0192_basicevent_alter_event_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="api_error_timeout_seconds",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="api_final_update_timeout_seconds",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="api_request_timeout_seconds",
            field=models.IntegerField(
                blank=True, db_column="api_timeout_seconds", null=True
            ),
        ),
        migrations.AddField(
            model_name="task",
            name="api_resume_delay_seconds",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="api_retry_delay_seconds",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="api_task_execution_creation_conflict_retry_delay_seconds",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="api_task_execution_creation_conflict_timeout_seconds",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="api_task_execution_creation_error_timeout_seconds",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="ignore_stderr",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="ignore_stdout",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="max_log_line_length",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="merge_stdout_and_stderr_logs",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="num_log_lines_sent_on_failure",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="num_log_lines_sent_on_success",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="num_log_lines_sent_on_timeout",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="prevent_offline_execution",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="process_command",
            field=models.CharField(max_length=5000, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="process_max_retries",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="process_retry_delay_seconds",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="process_termination_grace_period_seconds",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="process_timeout_seconds",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="status_update_interval_seconds",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="status_update_message_max_bytes",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="task",
            name="status_update_port",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="taskexecution",
            name="failure_report_probability",
            field=models.FloatField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0.0),
                    django.core.validators.MaxValueValidator(1.0),
                ],
            ),
        ),
        migrations.AddField(
            model_name="taskexecution",
            name="ignore_stderr",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="taskexecution",
            name="ignore_stdout",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="taskexecution",
            name="managed_probability",
            field=models.FloatField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0.0),
                    django.core.validators.MaxValueValidator(1.0),
                ],
            ),
        ),
        migrations.AddField(
            model_name="taskexecution",
            name="max_log_line_length",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="taskexecution",
            name="merge_stdout_and_stderr_logs",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="taskexecution",
            name="num_log_lines_sent_on_failure",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="taskexecution",
            name="num_log_lines_sent_on_success",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="taskexecution",
            name="num_log_lines_sent_on_timeout",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="taskexecution",
            name="other_metadata",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="taskexecution",
            name="timeout_report_probability",
            field=models.FloatField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0.0),
                    django.core.validators.MaxValueValidator(1.0),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="failure_report_probability",
            field=models.FloatField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0.0),
                    django.core.validators.MaxValueValidator(1.0),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="managed_probability",
            field=models.FloatField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0.0),
                    django.core.validators.MaxValueValidator(1.0),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="task",
            name="timeout_report_probability",
            field=models.FloatField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0.0),
                    django.core.validators.MaxValueValidator(1.0),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="taskexecution",
            name="allocated_cpu_units",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="taskexecution",
            name="allocated_memory_mb",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]

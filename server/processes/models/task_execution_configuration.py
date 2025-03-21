from django.db import models

from django.core.validators import MaxValueValidator, MinValueValidator

from .infrastructure_configuration import InfrastructureConfiguration

class TaskExecutionConfiguration(InfrastructureConfiguration):
    class Meta:
        abstract = True

    process_command = models.CharField(max_length=5000, null=True)
    allocated_cpu_units = models.PositiveIntegerField(null=True, blank=True)
    allocated_memory_mb = models.PositiveIntegerField(null=True, blank=True)

    # TODO: use when running - might need to pass to process wrapper for
    # scheduled processes
    environment_variables_overrides = models.JSONField(null=True, blank=True)

    prevent_offline_execution = models.BooleanField(null=True, blank=True)
    process_timeout_seconds = models.IntegerField(null=True, blank=True)
    process_max_retries = models.IntegerField(null=True, blank=True)
    process_retry_delay_seconds = models.PositiveIntegerField(null=True, blank=True)
    process_termination_grace_period_seconds = models.IntegerField(null=True, blank=True)

    api_retry_delay_seconds = models.PositiveIntegerField(null=True, blank=True)
    api_resume_delay_seconds = models.PositiveIntegerField(null=True, blank=True)
    api_error_timeout_seconds = models.IntegerField(null=True, blank=True)
    api_task_execution_creation_error_timeout_seconds = models.IntegerField(null=True, blank=True)
    api_task_execution_creation_conflict_timeout_seconds = models.IntegerField(null=True, blank=True)
    api_task_execution_creation_conflict_retry_delay_seconds = models.PositiveIntegerField(null=True, blank=True)
    api_final_update_timeout_seconds = models.IntegerField(null=True, blank=True)
    api_request_timeout_seconds = models.IntegerField(null=True, blank=True,
            db_column='api_timeout_seconds')

    status_update_interval_seconds = models.IntegerField(null=True, blank=True)
    status_update_port = models.IntegerField(null=True, blank=True)
    status_update_message_max_bytes = models.IntegerField(null=True, blank=True)

    num_log_lines_sent_on_failure = models.PositiveIntegerField(null=True, blank=True)
    num_log_lines_sent_on_timeout = models.PositiveIntegerField(null=True, blank=True)
    num_log_lines_sent_on_success = models.PositiveIntegerField(null=True, blank=True)
    max_log_line_length = models.PositiveIntegerField(null=True, blank=True)
    merge_stdout_and_stderr_logs = models.BooleanField(null=True, blank=True)
    ignore_stdout = models.BooleanField(null=True, blank=True)
    ignore_stderr = models.BooleanField(null=True, blank=True)

    managed_probability =  models.FloatField(null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    failure_report_probability =  models.FloatField(null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    timeout_report_probability =  models.FloatField(null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])

    other_metadata = models.JSONField(null=True, blank=True)
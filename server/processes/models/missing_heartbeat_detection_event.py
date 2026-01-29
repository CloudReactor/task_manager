from django.db import models

from .task_execution_event import TaskExecutionEvent


class MissingHeartbeatDetectionEvent(TaskExecutionEvent):
    MISSING_HEARTBEAT_EVENT_SUMMARY_TEMPLATE = \
"""Execution {{task_execution.uuid}} of the Task '{{task.name}}' has not sent a heartbeat for more than {{heartbeat_interval_seconds}} seconds after the previous heartbeat at {{last_heartbeat_at}}"""

    MISSING_HEARTBEAT_EVENT_DETAILS_TEMPLATE = \
"""Execution {{task_execution.uuid}} of the Task '{{task.name}}' has not sent a heartbeat for more than {{heartbeat_interval_seconds}}.
Expected heartbeat at {{expected_heartbeat_at}} but last heartbeat was at {{last_heartbeat_at}}."""

    FOUND_HEARTBEAT_EVENT_SUMMARY_TEMPLATE = \
"""Execution {{task_execution.uuid}} of the Task '{{task.name}}' has sent a late heartbeat after being marked as missing a heartbeat"""

    FOUND_HEARTBEAT_EVENT_DETAILS_TEMPLATE = \
"""Execution {{task_execution.uuid}} of the Task '{{task.name}}' has sent a late heartbeat at {{last_heartbeat_at}} after being marked as missing a heartbeat."""

    last_heartbeat_at = models.DateTimeField(null=True)
    expected_heartbeat_at = models.DateTimeField(null=True)
    heartbeat_interval_seconds = models.IntegerField(null=True)

    class Meta:
        ordering = ['event_at', 'detected_at']

    def __init__(self, *args, **kwargs):
        from ..services.notification_generator import NotificationGenerator

        super().__init__(*args, **kwargs)

        if self.resolved_event:
            summary_template = self.FOUND_HEARTBEAT_EVENT_SUMMARY_TEMPLATE
            details_template = self.FOUND_HEARTBEAT_EVENT_DETAILS_TEMPLATE
        else:
            summary_template = self.MISSING_HEARTBEAT_EVENT_SUMMARY_TEMPLATE
            details_template = self.MISSING_HEARTBEAT_EVENT_DETAILS_TEMPLATE

        notification_generator = NotificationGenerator()

        template_params = notification_generator.make_template_params(
                task_execution=self.task_execution,
                severity=self.severity_label)

        extra_params = {
            'heartbeat_interval_seconds': self.heartbeat_interval_seconds,
            'expected_heartbeat_at': self.expected_heartbeat_at,
            'last_heartbeat_at': self.last_heartbeat_at,
        }

        template_params = {**template_params, **extra_params}

        self.error_summary = notification_generator.generate_text(
                template_params=template_params,
                template=summary_template,
                task_execution=self.task_execution)

        self.error_details_message = notification_generator.generate_text(
                template_params=template_params,
                template=details_template,
                task_execution=self.task_execution)

from typing import Optional

from django.db import models

from .execution import Execution
from .schedulable_instance_event import SchedulableInstanceEvent


class MissingScheduledExecutionEvent(SchedulableInstanceEvent):
    MISSING_SCHEDULED_EXECUTION_SUMMARY_TEMPLATE = \
        """{{type_label}} '{{instance.name}}' did not execute as scheduled at {{expected_execution_at}}"""

    FOUND_SCHEDULED_EXECUTION_SUMMARY_TEMPLATE = \
        """{{type_label}} '{{instance.name}}' has started after being late according to its schedule"""

    class Meta:
        ordering = ['event_at', 'detected_at']

    expected_execution_at = models.DateTimeField(null=True, blank=True)
    schedule = models.CharField(null=True, blank=True, max_length=1000)
    missing_execution_count = models.PositiveIntegerField(default=0, null=True, blank=True)


    def __init__(self, *args, **kwargs):
        from ..services.notification_generator import NotificationGenerator

        super().__init__(*args, **kwargs)

        self.event_at = self.expected_execution_at

        instance = self.schedulable_instance

        self.severity = instance.notification_event_severity_on_missing_execution

        label = instance.kind_label

        epoch_minutes = divmod(self.expected_execution_at.timestamp(), 60)[0]

        self.grouping_key = f"missing_scheduled_{label.lower()}-{instance.uuid}-{epoch_minutes}"

        summary_template = self.FOUND_SCHEDULED_EXECUTION_SUMMARY_TEMPLATE if \
            self.resolved_event else self.MISSING_SCHEDULED_EXECUTION_SUMMARY_TEMPLATE

        notification_generator = NotificationGenerator()

        template_params = notification_generator.make_template_params(
            task=getattr(self, 'task'),
            workflow=getattr(self, 'workflow'),
            is_resolution=self.is_resolution,
            severity=self.severity_label)

        template_params['type_label'] = label
        template_params['instance'] = instance
        template_params['expected_execution_at'] = self.expected_execution_at

        self.error_summary = notification_generator.generate_text(
            template_params=template_params,
            template=summary_template)

    @property
    def resolving_execution(self) -> Optional[Execution]:
        raise NotImplementedError()

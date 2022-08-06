from typing import Any, Optional

import logging

from django.db import models

from processes.common.pagerduty import *

from .pagerduty_profile import PagerDutyProfile
from .email_notification_profile import EmailNotificationProfile
from .named_with_uuid_and_run_environment_model import NamedWithUuidAndRunEnvironmentModel
from .task_execution import TaskExecution
from .workflow_execution import WorkflowExecution

logger = logging.getLogger(__name__)


class AlertMethod(NamedWithUuidAndRunEnvironmentModel):
    """
    An AlertMethod specifies one or more configured methods of notifying
    users or external sources of events that trigger when one or more
    conditions are satisfied.
    """

    class Meta:
        unique_together = (('name', 'created_by_group'),)

    notify_on_success = models.BooleanField(default=False)
    notify_on_failure = models.BooleanField(default=True)
    notify_on_timeout = models.BooleanField(default=True)
    error_severity_on_missing_execution = models.CharField(
        max_length=10, blank=True, default='error',
        choices=PAGERDUTY_EVENT_SEVERITY_CHOICES)
    error_severity_on_missing_heartbeat = models.CharField(
        max_length=10, blank=True, default='warning',
        choices=PAGERDUTY_EVENT_SEVERITY_CHOICES)
    error_severity_on_service_down = models.CharField(
        max_length=10, blank=True, default='error',
        choices=PAGERDUTY_EVENT_SEVERITY_CHOICES)

    pagerduty_profile = models.ForeignKey(
        PagerDutyProfile, on_delete=models.CASCADE, null=True, blank=True)
    pagerduty_event_severity = models.CharField(
        max_length=10, blank=True, choices=PAGERDUTY_EVENT_SEVERITY_CHOICES)

    pagerduty_event_group_template = models.CharField(max_length=1000, blank=True)
    pagerduty_event_class_template = models.CharField(max_length=1000, blank=True)

    email_notification_profile = models.ForeignKey(
        EmailNotificationProfile, on_delete=models.CASCADE, null=True, blank=True)

    enabled = models.BooleanField(default=True)

    def send(self, details: Optional[dict[str, Any]] = None,
             severity: Optional[str] = None, source: Optional[str] = None,
             summary_template: Optional[str] = None,
             task_execution: Optional[TaskExecution] = None,
             workflow_execution: Optional[WorkflowExecution] = None,
             grouping_key: Optional[str] = None,
             is_resolution: bool = False):

        if not self.enabled:
            logger.info(f"Skipping alert method {self.uuid} / {self.name} because it is disabled")
            return None

        if self.email_notification_profile:
            return self.email_notification_profile.send(
                details=details,
                severity=severity,
                subject_template=summary_template,
                task_execution=task_execution,
                workflow_execution=workflow_execution,
                is_resolution=is_resolution)

        if self.pagerduty_profile:
            return self.pagerduty_profile.send(
                details=details,
                severity=severity or self.pagerduty_event_severity,
                source=source, summary_template=summary_template,
                task_execution=task_execution,
                workflow_execution=workflow_execution,
                grouping_key=grouping_key,
                is_resolution=is_resolution,
                event_group_template=self.pagerduty_event_group_template,
                event_class_template=self.pagerduty_event_class_template)

        logger.warning(f"Unknown alert method type for {self.uuid}")
        return None

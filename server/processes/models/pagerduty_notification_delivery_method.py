from __future__ import annotations

from typing import Any, cast

import logging

from django.conf import settings
from django.db import models

import pagerduty

from ..common.notification import *
from .event import Event
from .notification_delivery_method import NotificationDeliveryMethod

logger = logging.getLogger(__name__)


class PagerDutyNotificationDeliveryMethod(NotificationDeliveryMethod):
    pagerduty_api_key = models.CharField(max_length=1000, null=True)
    pagerduty_event_class_template = models.CharField(max_length=1000, null=True, blank=True)
    pagerduty_event_component_template = models.CharField(max_length=1000, null=True, blank=True)
    pagerduty_event_group_template = models.CharField(max_length=1000, null=True, blank=True)

    @staticmethod
    def pagerduty_severity_from_event_severity(severity: int) -> str:
        if severity >= Event.Severity.CRITICAL:
            return 'critical'
        
        if severity >= Event.Severity.ERROR:
            return 'error'
        
        if severity >= Event.Severity.WARNING:
            return 'warning'
        
        return 'info'

    def send(self, event: Event) -> dict[str, Any] | None:
        from .task_execution import TaskExecution
        from .workflow_execution import WorkflowExecution
        from .task_execution_status_change_event import TaskExecutionStatusChangeEvent
        from .workflow_execution_status_change_event import WorkflowExecutionStatusChangeEvent

        from ..services import NotificationGenerator

        severity = DEFAULT_NOTIFICATION_ERROR_SEVERITY
        if event.is_resolution:
            severity = DEFAULT_NOTIFICATION_RESOLUTION_SEVERITY

        task_execution: TaskExecution | None = None
        workflow_execution: WorkflowExecution | None = None

        if isinstance(event, TaskExecutionStatusChangeEvent):
            task_execution = cast(TaskExecutionStatusChangeEvent, event).task_execution
        elif isinstance(event, WorkflowExecutionStatusChangeEvent):
            workflow_execution = cast(WorkflowExecutionStatusChangeEvent, event).workflow_execution

        notification_generator = NotificationGenerator()

        template_params = notification_generator.make_template_params(
            task_execution=task_execution,
            workflow_execution=workflow_execution,
            is_resolution=event.is_resolution,
            severity=severity)

        source = event.source or DEFAULT_NOTIFICATION_SOURCE
        template_params['source'] = source

        if event.details:
            template_params.update(event.details)

        with pagerduty.EventsApiV2Client(self.pagerduty_api_key,
                debug=False) as events_client:

            if event.is_resolution:
                return {
                    'resolve_return_value': events_client.resolve(dedup_key=event.grouping_key)
                }

            payload: dict[str, Any] = {}

            if self.pagerduty_event_class_template:
                payload['class'] = notification_generator.generate_text(
                    template_params=template_params,
                    template=self.pagerduty_event_class_template,
                    task_execution=task_execution,
                    workflow_execution=workflow_execution).strip()

            if self.pagerduty_event_component_template:
                payload['component'] = notification_generator.generate_text(
                    template_params=template_params,
                    template=self.pagerduty_event_component_template,
                    task_execution=task_execution,
                    workflow_execution=workflow_execution).strip()

            if self.pagerduty_event_group_template:
                payload['group'] = notification_generator.generate_text(
                    template_params=template_params,
                    template=self.pagerduty_event_group_template,
                    task_execution=task_execution,
                    workflow_execution=workflow_execution).strip()

            pd_severity = self.pagerduty_severity_from_event_severity(event.severity)
            base_url = settings.EXTERNAL_BASE_URL.rstrip('/')
            event_url = f"{base_url}/events/{event.uuid}"
            dedup_key = events_client.trigger(summary=event.error_summary,
                source=source,
                severity=pd_severity,
                dedup_key=event.grouping_key,
                payload=payload,
                custom_details=template_params,
                links=[{'href': event_url, 'text': 'View Event in CloudReactor'}])

            logger.info(f"Done triggering PagerDuty event, {dedup_key=}")

            return {
                'dedup_key': dedup_key
            }

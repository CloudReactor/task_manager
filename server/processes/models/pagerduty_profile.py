from typing import Any, Dict, Optional

import logging

from django.db import models

# Note: pypd is deprecated as of 6/23/2020
import pypd

from processes.common.pagerduty import *
from .named_with_uuid_and_run_environment_model import NamedWithUuidAndRunEnvironmentModel
from .task_execution import TaskExecution
from .workflow_execution import WorkflowExecution

logger = logging.getLogger(__name__)


class PagerDutyProfile(NamedWithUuidAndRunEnvironmentModel):
    class Meta:
        unique_together = (('name', 'created_by_group'),)

    integration_key = models.CharField(max_length=1000)
    default_event_severity = models.CharField(
        max_length=10, blank=True,
        choices=PAGERDUTY_EVENT_SEVERITY_CHOICES)
    default_event_component_template = models.CharField(max_length=1000, blank=True)
    default_event_group_template = models.CharField(max_length=1000, blank=True)
    default_event_class_template = models.CharField(max_length=1000, blank=True)

    def send(self, details: Optional[Dict[str, Any]] = None,
            severity: Optional[str] = None, source: Optional[str] = None,
            summary_template: Optional[str] = None,
            task_execution: Optional[TaskExecution] = None,
            workflow_execution: Optional[WorkflowExecution] = None,
            grouping_key: Optional[str] = None, is_resolution: bool = False,
            event_group_template: Optional[str] = None,
            event_class_template: Optional[str] = None) -> str:
        from processes.services import NotificationGenerator

        if not severity:
            if is_resolution:
                severity = DEFAULT_PAGERDUTY_EVENT_RESOLUTION_SEVERITY
            else:
                severity = DEFAULT_PAGERDUTY_EVENT_ERROR_SEVERITY

        notification_generator = NotificationGenerator()

        template_params = notification_generator.make_template_params(
            task_execution=task_execution,
            workflow_execution=workflow_execution,
            is_resolution=is_resolution,
            severity=severity)

        if details:
            template_params.update(details)

        if not source:
            source = DEFAULT_PAGERDUTY_EVENT_SOURCE

        template_params['source'] = source

        if workflow_execution:
            summary_template = summary_template or DEFAULT_PAGERDUTY_EVENT_WORKFLOW_EXECUTION_SUMMARY_TEMPLATE
        else:
            summary_template = summary_template or DEFAULT_PAGERDUTY_EVENT_TASK_EXECUTION_SUMMARY_TEMPLATE

        if task_execution:
            summary_template = summary_template or DEFAULT_PAGERDUTY_EVENT_TASK_EXECUTION_SUMMARY_TEMPLATE

        event_summary = notification_generator.generate_text(
            template_params=template_params,
            template=summary_template,
            task_execution=task_execution,
            workflow_execution=workflow_execution,
            is_resolution=is_resolution)

        event_class = event_class_template or self.default_event_class_template

        if event_class:
            event_class = notification_generator.generate_text(
                template_params=template_params,
                template=event_class,
                task_execution=task_execution,
                workflow_execution=workflow_execution,
                is_resolution=is_resolution)

        event_group = event_group_template or self.default_event_group_template

        if event_group:
            event_group = notification_generator.generate_text(
                template_params=template_params,
                template=event_group,
                task_execution=task_execution,
                workflow_execution=workflow_execution,
                is_resolution=is_resolution)

        event_action = 'resolve' if is_resolution else 'trigger'

        logger.info('Notifying PagerDuty ...')

        data = {
            'routing_key': self.integration_key,
            'event_action': event_action,
            'payload': {
                'summary': event_summary,
                'severity': severity,
                'source': source,
                'group': event_group,
                'class': event_class,
                'custom_details': template_params
            }
        }

        if grouping_key:
            data['dedup_key'] = grouping_key

        response = pypd.EventV2.create(data=data)

        logger.info('Done notifying PagerDuty')
        return response.get('dedup_key', '')

from __future__ import annotations

import logging

from django.db import models
from django.utils import timezone

from processes.models.task_execution import TaskExecution

from .event import Event
from .task_execution_event import TaskExecutionEvent


logger = logging.getLogger(__name__)


class DelayedTaskExecutionStartEvent(TaskExecutionEvent):

    SUMMARY_TEMPLATE = \
        "Execution {task_execution.task.uuid} of Task '{task_execution.task.name}' was initiated at {task_execution.started_at} but not started yet after {delay_before_event_seconds} seconds"

    RESOLUTION_SUMMARY_TEMPLATE = \
        "Task '{task_execution.task.name}' has started after being manually started and being late to start"

    @classmethod
    def resolve_existing_for_task_execution(cls, task_execution: TaskExecution) -> DelayedTaskExecutionStartEvent | None:
        existing_dtese = cls.objects.filter(task_execution=task_execution, resolved_at__isnull=True) \
                .order_by('-event_at', '-created_at').first()

        if existing_dtese:
            return existing_dtese.resolve()

        return None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        if self.task:
            if not self.grouping_key:
                self.grouping_key = f"delayed_task_start-{self.task.uuid}"

            delay_before_event_seconds: int | None = None
            if not self.resolved_at:
                delay_before_event_seconds = self.task.max_manual_start_delay_before_alert_seconds

            if (not self.desired_start_at) and self.task_execution:
                self.desired_start_at = self.task_execution.started_at
                if self.desired_start_at:
                    self.desired_start_at = self.desired_start_at.replace(microsecond=0)

            if (not self.expected_start_by_deadline) and self.desired_start_at and (delay_before_event_seconds is not None):
                self.expected_start_by_deadline = (self.desired_start_at + \
                    timezone.timedelta(seconds=delay_before_event_seconds)).replace(microsecond=0)

            if self.severity is None:
                if self.resolved_at:
                    self.severity = Event.Severity.INFO
                else:
                    self.severity = self.task.notification_event_severity_on_missing_execution

            if (not self.error_summary) and self.task_execution and (delay_before_event_seconds is not None):
                template = self.RESOLUTION_SUMMARY_TEMPLATE if self.resolved_at else self.SUMMARY_TEMPLATE
                self.error_summary = template.format(task_execution=self.task_execution, delay_before_event_seconds=delay_before_event_seconds)

    def resolve(self) -> DelayedTaskExecutionStartEvent | None:
        if self.resolved_at:
            logger.info(f"Delayed Task Execution Start Event {self.uuid} is already resolved")
            return None

        utc_now = timezone.now()
        self.resolved_at = utc_now
        self.resolved_by_user = None
        self.source = Event.SOURCE_SYSTEM
        self.save()

        resolving_event = DelayedTaskExecutionStartEvent(
                event_at=utc_now,
                detected_at=utc_now,
                severity=Event.Severity.INFO,
                task_execution=self.task_execution,
                desired_start_at=self.desired_start_at,
                expected_start_by_deadline=self.expected_start_by_deadline,
                resolved_event=self,
                resolved_at=utc_now,
        )
        resolving_event.save()

        self.send_event_notifications(resolving_event)

        return resolving_event

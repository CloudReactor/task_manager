from __future__ import annotations

from typing import override

from enum import IntEnum, unique
import logging
import uuid

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User, Group

from typedmodels.models import TypedModel

from .subscription import Subscription


logger = logging.getLogger(__name__)


class Event(TypedModel):
    @unique
    class Severity(IntEnum):
        CRITICAL = 600
        ERROR = 500
        WARNING = 400
        INFO = 300
        DEBUG = 200
        TRACE = 100
        NONE = 0

    # NOTE: severity labels are derived from the enum names where needed.
    # The special `NONE` value is handled by `severity_label`.

    SOURCE_SYSTEM = 'system'

    MAX_ERROR_SUMMARY_LENGTH = 200
    MAX_ERROR_DETAILS_MESSAGE_LENGTH = 50000
    MAX_SOURCE_LENGTH = 1000
    MAX_GROUPING_KEY_LENGTH = 5000

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    event_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    detected_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, editable=True,
            related_name='acknowledged_events')
    severity = models.PositiveIntegerField(default=Severity.ERROR)
    error_summary = models.CharField(max_length=MAX_ERROR_SUMMARY_LENGTH, blank=True)
    error_details_message = models.CharField(max_length=MAX_ERROR_DETAILS_MESSAGE_LENGTH, blank=True)
    source = models.CharField(max_length=MAX_SOURCE_LENGTH, blank=True)
    details = models.JSONField(null=True, blank=True)
    grouping_key = models.CharField(max_length=MAX_GROUPING_KEY_LENGTH, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, editable=True,
            related_name='resolved_events')
    resolved_event = models.OneToOneField('self', on_delete=models.DO_NOTHING, null=True, blank=True)

    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL,
            null=True, blank=True, editable=True)

    # null=True until we can populate this field for existing events
    created_by_group = models.ForeignKey(Group, on_delete=models.CASCADE,
            null=True, blank=True, editable=True)

    run_environment = models.ForeignKey('RunEnvironment',
        related_name='+', on_delete=models.CASCADE, blank=True, null=True)

    # Fields added for specific event types but stored on base Event table
    task = models.ForeignKey('Task', null=True, blank=True, on_delete=models.CASCADE)
    workflow = models.ForeignKey('Workflow', null=True, blank=True, on_delete=models.CASCADE)
    task_execution = models.ForeignKey('TaskExecution', null=True, blank=True, on_delete=models.CASCADE)
    workflow_execution = models.ForeignKey('WorkflowExecution', null=True, blank=True, on_delete=models.CASCADE)

    # Heartbeat fields (for MissingHeartbeatDetectionEvent)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    expected_heartbeat_at = models.DateTimeField(null=True, blank=True)
    heartbeat_interval_seconds = models.IntegerField(null=True, blank=True)

    # Status change fields (for ExecutionStatusChangeEvent)
    status = models.IntegerField(null=True, blank=True)
    postponed_until = models.DateTimeField(null=True, blank=True)
    count_with_same_status_after_postponement = models.IntegerField(null=True, blank=True)
    count_with_success_status_after_postponement = models.IntegerField(null=True, blank=True)
    triggered_at = models.DateTimeField(null=True, blank=True)

    # Scheduled execution fields (for MissingScheduledExecutionEvent)
    expected_execution_at = models.DateTimeField(null=True, blank=True)
    schedule = models.CharField(max_length=1000, null=True, blank=True)
    missing_execution_count = models.PositiveIntegerField(default=0, null=True, blank=True)

    # Delayed start fields (for DelayedTaskExecutionStartEvent)
    desired_start_at = models.DateTimeField(null=True, blank=True)
    expected_start_by_deadline = models.DateTimeField(null=True, blank=True)

    # Insufficient service fields (for InsufficientServiceTaskExecutionsEvent)
    interval_start_at = models.DateTimeField(null=True, blank=True)
    interval_end_at = models.DateTimeField(null=True, blank=True)
    detected_concurrency = models.IntegerField(null=True, blank=True)
    required_concurrency = models.IntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_by_group', 'event_at']),
            models.Index(fields=['run_environment', 'event_at']),
        ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        if not self.source:
            self.source = self.SOURCE_SYSTEM

    def save(self, *args, **kwargs) -> None:
        logger.info(f"pre-save with Event {self.uuid}, {self._state.adding=}, {self.created_by_group=}")

        # https://stackoverflow.com/questions/2037320/what-is-the-canonical-way-to-find-out-if-a-django-model-is-saved-to-db
        if self._state.adding:
            group = self.created_by_group

            if (group is None) and self.run_environment:
                group = self.run_environment.created_by_group
                self.created_by_group = group

            if group is None:
                logger.warning(f"Event {self.uuid} has no group")
            else:
                existing_event_count = Event.objects.filter(created_by_group=group).count()
                usage_limits = Subscription.compute_usage_limits(group)
                max_events = usage_limits.max_events

                if (max_events is not None) and (existing_event_count >= max_events):
                    diff = existing_event_count - max_events + 1
                    for event in Event.objects.filter(created_by_group=group) \
                            .order_by('event_at').all()[:diff].iterator():

                        id = event.uuid
                        logger.info(f"Deleting Event {id} because {group=} has reached the limit of {max_events}")

                        try:
                            event.delete()
                            logger.info(f"Deleted Event {id} successfully")
                        except Exception:
                            logger.warning(f"Failed to delete Event {id}", exc_info=True)
        else:
            logger.info('Updating an existing Event')

        super().save(*args, **kwargs)


    @property
    def severity_label(self) -> str:
        try:
            sev = self.Severity(self.severity)
        except Exception:
            return 'unknown'

        return sev.name.lower()

    @property
    def is_resolution(self) -> bool:
        return self.resolved_event is not None

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>, {self.error_summary}"


class BasicEvent(Event):
    pass

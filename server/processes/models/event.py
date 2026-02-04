from __future__ import annotations

from typing import TYPE_CHECKING

import logging
import uuid

from django.db import models
from django.utils import timezone

from django.contrib.auth.models import Group

from typedmodels.models import TypedModel
from enum import IntEnum, unique

from .subscription import Subscription

if TYPE_CHECKING:
    from .run_environment import RunEnvironment

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

    MAX_ERROR_SUMMARY_LENGTH = 200
    MAX_ERROR_DETAILS_MESSAGE_LENGTH = 50000
    MAX_SOURCE_LENGTH = 1000
    MAX_GROUPING_KEY_LENGTH = 5000

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    event_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    detected_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    severity = models.PositiveIntegerField(default=Severity.ERROR)
    error_summary = models.CharField(max_length=MAX_ERROR_SUMMARY_LENGTH, blank=True)
    error_details_message = models.CharField(max_length=MAX_ERROR_DETAILS_MESSAGE_LENGTH, blank=True)
    source = models.CharField(max_length=MAX_SOURCE_LENGTH, blank=True)
    details = models.JSONField(null=True, blank=True)
    grouping_key = models.CharField(max_length=MAX_GROUPING_KEY_LENGTH, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_event = models.OneToOneField('self', on_delete=models.DO_NOTHING, null=True, blank=True)

    # null=True until we can populate this field for existing events
    created_by_group = models.ForeignKey(Group, on_delete=models.CASCADE,
            null=True, blank=True, editable=True)

    run_environment = models.ForeignKey('RunEnvironment',
        related_name='+', on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_by_group', 'event_at']),
            models.Index(fields=['run_environment', 'event_at']),
        ]


    def save(self, *args, **kwargs) -> None:
        logger.info(f"pre-save with Event {self.uuid}, {self._state.adding=}, {self.created_by_group=}")

        # https://stackoverflow.com/questions/2037320/what-is-the-canonical-way-to-find-out-if-a-django-model-is-saved-to-db
        if self._state.adding:
            group = self.created_by_group

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
    def severity_label(self):
        try:
            sev = self.Severity(self.severity)
        except Exception:
            return 'unknown'

        return sev.name.lower()

    @property
    def is_resolution(self):
        return self.resolved_event is not None

    def __repr__(self):
        return f"<{self.__class__.__name__}>, {self.error_summary}"


class BasicEvent(Event):
    pass

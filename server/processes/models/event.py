import logging
import uuid

from django.db import models
from django.utils import timezone

from django.contrib.auth.models import Group

from typedmodels.models import TypedModel

from .subscription import Subscription

logger = logging.getLogger(__name__)


class Event(TypedModel):
    SEVERITY_CRITICAL = 600
    SEVERITY_ERROR = 500
    SEVERITY_WARNING = 400
    SEVERITY_INFO = 300
    SEVERITY_DEBUG = 200
    SEVERITY_TRACE = 100
    SEVERITY_NONE = 0

    # TODO: maybe use frozendict
    SEVERITY_TO_LABEL = {
        SEVERITY_CRITICAL: 'critical',
        SEVERITY_ERROR: 'error',
        SEVERITY_WARNING: 'warning',
        SEVERITY_INFO: 'info',
        SEVERITY_DEBUG: 'debug',
        SEVERITY_TRACE: 'trace',
        SEVERITY_NONE: 'none',
    }

    MAX_ERROR_SUMMARY_LENGTH = 200
    MAX_ERROR_DETAILS_MESSAGE_LENGTH = 50000
    MAX_SOURCE_LENGTH = 1000
    MAX_GROUPING_KEY_LENGTH = 5000

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    event_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    detected_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    severity = models.PositiveIntegerField(default=SEVERITY_ERROR)
    error_summary = models.CharField(max_length=MAX_ERROR_SUMMARY_LENGTH, blank=True)
    error_details_message = models.CharField(max_length=MAX_ERROR_DETAILS_MESSAGE_LENGTH, blank=True)
    source = models.CharField(max_length=MAX_SOURCE_LENGTH, blank=True)
    details = models.JSONField(null=True, blank=True)
    grouping_key = models.CharField(max_length=MAX_GROUPING_KEY_LENGTH, blank=True)
    resolved_at = models.DateTimeField(null=True)
    resolved_event = models.OneToOneField('self', on_delete=models.DO_NOTHING, null=True, blank=True)

    # null=True until we can populate this field for existing notifications
    created_by_group = models.ForeignKey(Group, on_delete=models.CASCADE,
            null=True, editable=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_by_group', 'event_at']),
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
        return self.SEVERITY_TO_LABEL.get(self.severity, 'unknown')

    @property
    def is_resolution(self):
        return self.resolved_event is not None

    def __repr__(self):
        return f"<{self.__class__.__name__}>, {self.error_summary}"


class BasicEvent(Event):
    pass

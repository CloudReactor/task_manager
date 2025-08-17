from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import enum
import logging

from django.contrib.auth.models import User
from django.db import models, transaction
from django.utils import timezone

from .uuid_model import UuidModel


if TYPE_CHECKING:
    from .schedulable import Schedulable
    from .event import Event



logger = logging.getLogger(__name__)


class Execution(UuidModel):
    class Meta:
        abstract = True

    @enum.unique
    class Status(enum.IntEnum):
        RUNNING = 0
        SUCCEEDED = 1
        FAILED = 2
        TERMINATED_AFTER_TIME_OUT = 3
        MARKED_DONE = 4
        EXITED_AFTER_MARKED_DONE = 5
        STOPPING = 6
        STOPPED = 7
        ABANDONED = 8
        MANUALLY_STARTED = 9
        ABORTED = 10

    input_value = models.JSONField(null=True, blank=True)
    output_value = models.JSONField(null=True, blank=True)

    run_reason = models.IntegerField(default=0)
    stop_reason = models.IntegerField(null=True, blank=True)

    status = models.IntegerField(default=Status.RUNNING.value)

    started_at = models.DateTimeField(default=timezone.now, blank=True)
    started_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                   blank=True, related_name='+')
    finished_at = models.DateTimeField(null=True, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    marked_done_at = models.DateTimeField(null=True, blank=True)
    marked_done_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                       blank=True, related_name='+')
    marked_outdated_at = models.DateTimeField(null=True, blank=True)
    kill_started_at = models.DateTimeField(null=True, blank=True)
    kill_finished_at = models.DateTimeField(null=True, blank=True)
    kill_error_code = models.IntegerField(null=True, blank=True)
    killed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                  blank=True, related_name='+')
    failed_attempts = models.PositiveIntegerField(default=0)
    timed_out_attempts = models.PositiveIntegerField(default=0)
    error_details = models.JSONField(null=True, blank=True)

    other_instance_metadata = models.JSONField(null=True, blank=True)
    other_runtime_metadata = models.JSONField(null=True, blank=True)

    def get_schedulable(self) -> Optional[Schedulable]:
        raise NotImplementedError()

    def send_event_notifications(self, event: Event) -> int:
        # TODO: use Execution specific notification profiles

        schedulable = self.get_schedulable()

        if schedulable:
            return schedulable.send_event_notifications(event)
        else:
            logger.warning("Skipping sending notifications since Schedulable is missing")
            return 0

    def resolve_missing_scheduled_execution_events(self) -> None:
        from ..services.schedule_checker import MAX_SCHEDULED_LATENESS_SECONDS

        schedulable = self.get_schedulable()

        if not schedulable:
            logger.warning("resolve_missing_scheduled_execution_events(): no scheduable instance found")
            return

        if not (self.started_at and schedulable.schedule):
            logger.debug("resolve_missing_scheduled_execution_events(): not started or scheduled")
            return

        for msee in schedulable.lookup_missing_scheduled_execution_events().filter(
                resolved_event__isnull=True, expected_execution_at__isnull=False, resolved_at__isnull=True) \
                .order_by('-event_at', '-expected_execution_at').iterator():
            utc_now = timezone.now()
            lateness_seconds = (utc_now - msee.expected_execution_at).total_seconds()
            logger.info(f"Found last missing scheduled {schedulable.kind_label} Execution event {msee.uuid}, lateness seconds = {lateness_seconds}")

            if lateness_seconds < MAX_SCHEDULED_LATENESS_SECONDS:
                logger.info(
                    f"{schedulable.kind_label} Execution {self.uuid} is {lateness_seconds} seconds after scheduled time of {msee.expected_execution_at}, creating resolving event ...")

                with transaction.atomic():
                    resolving_event = schedulable.make_resolved_missing_scheduled_execution_event(
                            detected_at=utc_now,
                            resolved_event=msee,
                            execution=self,
                    )

                    msee.resolved_at = utc_now
                    msee.save()

                self.send_event_notifications(event=resolving_event)
            else:
                logger.info(
                    f"{schedulable.kind_label} Execution {self.uuid} is too far ({lateness_seconds} seconds) after scheduled time of {msee.expected_execution_at}, not resolving events")

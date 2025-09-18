from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from datetime import timedelta
import enum
import logging

from django.contrib.auth.models import User
from django.db import models, transaction
from django.utils import timezone

from .uuid_model import UuidModel
from .schedulable import Schedulable

if TYPE_CHECKING:
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
        from ..services.schedule_checker import ScheduleChecker

        schedulable = self.get_schedulable()

        if not schedulable:
            logger.warning("resolve_missing_scheduled_execution_events(): no scheduable instance found")
            return

        if not (self.started_at and schedulable.schedule):
            logger.debug("resolve_missing_scheduled_execution_events(): not started or scheduled")
            return

        for msee in schedulable.lookup_missing_scheduled_execution_events().filter(
                resolved_event__isnull=True, expected_execution_at__isnull=False) \
                .order_by('-event_at', '-expected_execution_at').iterator():
            lateness_seconds = (self.started_at - msee.expected_execution_at).total_seconds()
            logger.info(f"Found last missing scheduled {schedulable.kind_label} Execution event {msee.uuid}, expected execution at {msee.expected_execution_at}, lateness seconds = {lateness_seconds}")

            if lateness_seconds < Schedulable.DEFAULT_MAX_SCHEDULED_LATENESS_SECONDS:
                logger.info(
                    f"{schedulable.kind_label} Execution {self.uuid} is {lateness_seconds} seconds after scheduled time of {msee.expected_execution_at}")

                with transaction.atomic():
                    utc_now = timezone.now()
                    started_at_from = msee.expected_execution_at
                    started_at_to = utc_now

                    m = Schedulable.RATE_REGEX.match(msee.schedule)

                    if m:
                        n = int(m.group(1))
                        time_unit = m.group(2).lower().rstrip('s')
                        relative_delta = ScheduleChecker.make_relative_delta(n, time_unit)
                        started_at_from -= relative_delta
                    else:
                        started_at_from -= timedelta(seconds=Schedulable.DEFAULT_MAX_EARLY_STARTUP_SECONDS)
                        started_at_to = msee.expected_execution_at + timedelta(seconds=Schedulable.DEFAULT_MAX_SCHEDULED_LATENESS_SECONDS)

                    logger.info(f"Looking for executions of {schedulable.kind_label} {schedulable.uuid} started between {started_at_from} and {started_at_to}")

                    execution_count = schedulable.executions().filter(
                        started_at__gte=started_at_from,
                        started_at__lte=started_at_to
                    ).count()

                    required_instance_count = max(1, schedulable.scheduled_instance_count)

                    missing_execution_count = required_instance_count - execution_count

                    logger.info(f"Found {execution_count} executions of {schedulable.kind_label} {schedulable.uuid} after the expected time of {msee.expected_execution_at}, which requires {required_instance_count} instances, so missing_execution_count is {missing_execution_count}")

                    if missing_execution_count != msee.missing_execution_count:
                        logger.info(f"Updating missing_execution_count of MissingScheduledExecutionEvent {msee.uuid} from {msee.missing_execution_count} to {missing_execution_count}")
                        msee.missing_execution_count = missing_execution_count
                        msee.save()

                        if msee.missing_execution_count <= 0:
                            logger.info(f"Resolving MissingScheduledExecutionEvent {msee.uuid} since missing_execution_count is 0 or less")

                            if msee.missing_execution_count < 0:
                                logger.error(f"MissingScheduledExecutionEvent {msee.uuid} has negative missing_execution_count {msee.missing_execution_count}, setting to 0 and marking resolved")
                                msee.missing_execution_count = 0

                            msee.resolved_at = msee.resolved_at or utc_now
                            msee.save()

                            resolving_event = schedulable.make_resolved_missing_scheduled_execution_event(
                                    detected_at=utc_now,
                                    resolved_event=msee,
                                    execution=self,
                            )

                            self.send_event_notifications(event=resolving_event)
                    else:
                        logger.info(f"Missing_execution_count of MissingScheduledExecutionEvent {msee.uuid} was {missing_execution_count} which stayed the same, not updating")
            else:
                logger.info(
                    f"{schedulable.kind_label} Execution {self.uuid} is too far ({lateness_seconds} seconds) after scheduled time of {msee.expected_execution_at}, not resolving events")

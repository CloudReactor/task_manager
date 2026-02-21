from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, Any, Type
from typing_extensions import Self

import copy
import enum
import logging

from django.contrib.auth.models import Group, User
from django.db import models, transaction
from django.utils import timezone

from .uuid_model import UuidModel
from .execution_probabilities import ExecutionProbabilities
from .event import Event
from .schedulable import Schedulable

if TYPE_CHECKING:
    from .run_environment import RunEnvironment
    from .execution_status_change_event import ExecutionStatusChangeEvent


logger = logging.getLogger(__name__)


class Execution(UuidModel, ExecutionProbabilities):
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

    IN_PROGRESS_STATUSES = [
        Status.MANUALLY_STARTED,
        Status.RUNNING,
    ]

    COMPLETED_STATUSES = [
        Status.SUCCEEDED,
        Status.FAILED,
        Status.TERMINATED_AFTER_TIME_OUT,
        Status.STOPPING,
        Status.STOPPED,
    ]

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

    # Transient properties
    skip_event_generation = False
    _loaded_copy: Execution | None = None


    @classmethod
    def from_db(cls: Type[Self], db: str, field_names: Sequence[str], values: Sequence[Any]):
        instance = super().from_db(db, field_names, values)
        instance._loaded_copy = copy.copy(instance)
        return instance

    def get_schedulable(self) -> Schedulable | None:
        raise NotImplementedError()

    def is_in_progress(self) -> bool:
        return self.status in Execution.IN_PROGRESS_STATUSES

    def is_successful(self) -> bool:
        return self.status == Execution.Status.SUCCEEDED

    @property
    def run_environment(self) -> RunEnvironment | None:
        schedulable = self.get_schedulable()
        if schedulable:
            return schedulable.run_environment
        
        return None
    
    @property
    def created_by_group(self) -> Group | None:
        schedulable = self.get_schedulable()
        if schedulable:
            if schedulable.created_by_group:
                return schedulable.created_by_group
            elif schedulable.run_environment:
                return schedulable.run_environment.created_by_group

        return None


    def maybe_create_and_send_status_change_event(self) -> ExecutionStatusChangeEvent | None:
        if self.skip_event_generation:
            logger.info("Skipping status change event creation since skip_event_generation = True")
            return None

        executable = self.get_schedulable()

        if executable is None:
            logger.info("Skipping status change event creation since Schedulable is missing")
            return None

        if not executable.enabled:
            logger.info(f"Skipping status change event creation since Schedulable {executable.uuid} is disabled")
            return None

        utc_now = timezone.now()

        if self.finished_at and \
            ((utc_now - self.finished_at).total_seconds() > self.MAX_STATUS_ALERT_AGE_SECONDS):
            logger.info(f"Skipping status change event creation since finished_at={self.finished_at} is too long ago")
            return None

        if not self.should_create_status_change_event():
            logger.info(f"Skipping status change event creation since Task {executable.uuid} should not create status change event")
            return None

        severity: int | None = Event.Severity.ERROR

        if self.status == Execution.Status.SUCCEEDED:
            severity = executable.notification_event_severity_on_success
        elif self.status == Execution.Status.FAILED:
            severity = executable.notification_event_severity_on_failure
        elif self.status == Execution.Status.TERMINATED_AFTER_TIME_OUT:
            severity = executable.notification_event_severity_on_timeout

        # TODO: default to Run Environment's severities, override with TaskExecution severities

        if (severity is None) or (severity == Event.Severity.NONE):
            logger.info(f"Skipping notifications since Schedulable {executable.uuid} has no severity set for status {self.status}")
            return None

        status_change_event = self.create_status_change_event(severity=severity)
        status_change_event.save()

        if status_change_event.maybe_postpone(schedulable=executable):
            logger.info(f"Postponing notifications on Task {executable.uuid} after execution status = {self.status}")
        else:
            logger.info(f"Not postponing notifications on Task {executable.uuid} after execution status = {self.status}")
            self.send_event_notifications(event=status_change_event)

        return status_change_event


    def should_create_status_change_event(self) -> bool:
        if self.skip_event_generation:        
            logger.info("Skipping status change event creation since skip_event_generation = True")
            return False

        executable = self.get_schedulable()

        if not executable:
            logger.info("Skipping status change event creation since Schedulable is missing")
            return False

        if not executable.enabled:
            logger.info(f"Skipping status change event creation since Schedulable {executable.uuid} is disabled")
            return False

        if self.status_change_event_queryset_for_execution().filter(status=self.status).exists():
            logger.info(f"Skipping status change event creation for Execution {self.uuid} since it already has a status change event")
            return False
                
        return True

    def create_status_change_event(self, severity: Event.Severity) -> ExecutionStatusChangeEvent:
        raise NotImplementedError()
    

    def update_postponed_status_change_events(self) -> int:
        executable = self.get_schedulable()

        if not executable:
            logger.warning("Skipping updating postponed notifications since Schedulable is missing")
            return 0

        if not executable.enabled:
            logger.info("Skipping updating postponed notifications since Schedulable is disabled")
            return 0


        status = self.status
        utc_now = timezone.now()
        events = self.status_change_event_queryset_for_executable().filter(
                postponed_until__isnull=False, postponed_until__gt=utc_now,
                resolved_at__isnull=True, triggered_at__isnull=True)

        if not events.exists():
            return 0

        updated_count = 0

        for event in events.all():
            if event.update_after_postponed(status=status, utc_now=utc_now):
                updated_count += 1

        return updated_count


    def status_change_event_queryset_for_execution(self) -> models.QuerySet:
        raise NotImplementedError()


    def status_change_event_queryset_for_executable(self) -> models.QuerySet:
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

        for msee in schedulable.lookup_missing_scheduled_execution_events().filter() \
                .order_by('-event_at', '-expected_execution_at').iterator():
            lateness_seconds = (self.started_at - msee.expected_execution_at).total_seconds()
            logger.info(f"Found last missing scheduled {schedulable.kind_label} Execution event {msee.uuid}, expected execution at {msee.expected_execution_at}, lateness seconds = {lateness_seconds}")

            if lateness_seconds < Schedulable.DEFAULT_MAX_SCHEDULED_LATENESS_SECONDS:
                logger.info(
                    f"{schedulable.kind_label} Execution {self.uuid} is {lateness_seconds} seconds after scheduled time of {msee.expected_execution_at}")

                with transaction.atomic():
                    utc_now = timezone.now()
                    time_range = ScheduleChecker.execution_time_range(schedulable, utc_now)
                    if not time_range:
                        logger.warning("Could not determine execution time range, skipping")
                        continue

                    _expected_time_range, started_at_from, started_at_to = time_range

                    logger.info(f"Looking for executions of {schedulable.kind_label} {schedulable.uuid} started between {started_at_from} and {started_at_to}")

                    execution_count = schedulable.executions().filter(
                        started_at__gte=started_at_from,
                        started_at__lte=started_at_to
                    ).count()

                    required_instance_count = max(1, schedulable.scheduled_instance_count or 1)

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

from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime
import logging
import re

from django.db import models
from django.db.models import Manager
from django.utils import timezone

from .event import Event
from .execution_probabilities import ExecutionProbabilities
from .named_with_uuid_model import NamedWithUuidModel
from .run_environment import RunEnvironment
from .notification_profile import NotificationProfile

if TYPE_CHECKING:
    from .execution import Execution
    from .missing_scheduled_execution_event import MissingScheduledExecutionEvent


logger = logging.getLogger(__name__)


SCHEDULE_TYPE_CRON = 'C'
SCHEDULE_TYPE_RATE = 'R'


class Schedulable(NamedWithUuidModel, ExecutionProbabilities):

    DEFAULT_MAX_EARLY_STARTUP_SECONDS = 60
    DEFAULT_MAX_STARTUP_SECONDS = 10 * 60
    DEFAULT_MAX_SCHEDULED_LATENESS_SECONDS = 30 * 60

    CRON_REGEX = re.compile(r"cron\s*\(([^)]+)\)")
    RATE_REGEX = re.compile(r"rate\s*\((\d+)\s+([A-Za-z]+)\)")

    class Meta:
        abstract = True

    run_environment = models.ForeignKey(RunEnvironment,
        related_name='+', on_delete=models.CASCADE, blank=True, null=True)

    notification_profiles = models.ManyToManyField(NotificationProfile)

    schedule = models.CharField(max_length=1000, blank=True)
    scheduled_instance_count = models.PositiveIntegerField(null=True, blank=True)
    schedule_updated_at = models.DateTimeField(default=timezone.now)
    max_concurrency = models.IntegerField(null=True, blank=True)
    enabled = models.BooleanField(default=True)

    max_age_seconds = models.PositiveIntegerField(null=True, blank=True)
    default_max_retries = models.PositiveIntegerField(default=0)
    postponed_failure_before_success_seconds = models.PositiveIntegerField(
        null=True, blank=True)
    max_postponed_failure_count = models.PositiveIntegerField(null=True,
        blank=True)
    required_success_count_to_clear_failure = models.PositiveIntegerField(
        null=True, blank=True)
    postponed_timeout_before_success_seconds = models.PositiveIntegerField(
        null=True, blank=True)
    max_postponed_timeout_count = models.PositiveIntegerField(null=True,
        blank=True)
    required_success_count_to_clear_timeout = models.PositiveIntegerField(
        null=True, blank=True)
    postponed_missing_execution_before_start_seconds = models.PositiveIntegerField(
        null=True, blank=True)
    max_postponed_missing_execution_count = models.PositiveIntegerField(null=True,
        blank=True)
    min_missing_execution_delay_seconds = models.PositiveIntegerField(null=True,
        blank=True)

    notification_event_severity_on_success = models.PositiveIntegerField(
        null=True, blank=True, default=None)
    notification_event_severity_on_failure = models.PositiveIntegerField(
        null=True, blank=True, default=Event.Severity.ERROR)
    notification_event_severity_on_timeout = models.PositiveIntegerField(
        null=True, blank=True, default=Event.Severity.ERROR)
    notification_event_severity_on_missing_execution = models.PositiveIntegerField(
        null=True, blank=True, default=Event.Severity.ERROR)
    notification_event_severity_on_missing_heartbeat = models.PositiveIntegerField(
        null=True, blank=True, default=Event.Severity.WARNING)
    notification_event_severity_on_service_down = models.PositiveIntegerField(
        null=True, blank=True, default=Event.Severity.ERROR)
    notification_event_severity_on_insufficient_instances = models.PositiveIntegerField(
        null=True, blank=True, default=Event.Severity.WARNING)
    notification_event_severity_on_sufficient_instances_restored = models.PositiveIntegerField(
        null=True, blank=True, default=Event.Severity.INFO)


    @property
    def kind_label(self) -> str:
        raise NotImplementedError()

    def concurrency_at(self, dt: datetime) -> int:
        raise NotImplementedError()

    def can_start_execution(self) -> bool:
        return False

    def executions(self) -> Manager[Execution]:
        raise NotImplementedError()

    @property
    def schedule_type(self) -> str | None:
        if self.schedule:
            if self.CRON_REGEX.match(self.schedule):
                return SCHEDULE_TYPE_CRON
            elif self.RATE_REGEX.match(self.schedule):
                return SCHEDULE_TYPE_RATE

        return None

    def lookup_all_missing_scheduled_execution_events(self) -> Manager[MissingScheduledExecutionEvent]:
        raise NotImplementedError()

    def lookup_missing_scheduled_execution_events(self) -> Manager[MissingScheduledExecutionEvent]:
        manager = self.lookup_all_missing_scheduled_execution_events()

        schedule_type = self.schedule_type
        if not schedule_type:
            return manager.none()

        return manager.filter(
                schedule=self.schedule, expected_execution_at__isnull=False, resolved_at__isnull=True,
                resolved_event__isnull=True)


    def make_resolved_missing_scheduled_execution_event(self, detected_at: datetime,
        resolved_event: MissingScheduledExecutionEvent, execution: Execution) -> MissingScheduledExecutionEvent:
        raise NotImplementedError()

    def send_event_notifications(self, event: Event) -> int:
        logger.info(f"Sending events for {self.kind_label} {self.name} ({self.uuid}) with event {event.uuid} ...")

        #run_env: Optional[RunEnvironment] = None

        #if hasattr(self, 'run_environment'):
        #    run_env = cast(RunEnvironment, self.run_environment)

        run_env = self.run_environment

        notification_profiles = self.notification_profiles.filter(enabled=True)

        # TODO: have a way to specify no Notification Profiles, not falling back to run_env
        if run_env and (not notification_profiles.exists()):
            logger.info(f"No Notification Profiles on {self.kind_label} {self.uuid}, checking Run Environment {run_env.uuid} ...")
            notification_profiles = run_env.notification_profiles.filter(enabled=True)

        count = 0

        for np in notification_profiles.all():
            try:
                logger.info(f"Sending event for {self.kind_label} {self.uuid} using Notification Profile {np.uuid} ...")

                np.send(event=event)

                logger.info(f"Done sending event for {self.kind_label} {self.uuid} using Notification Profile {np.uuid}")
                count += 1
            except Exception:
                logger.exception(f"Can't send using Notification Profile {np.uuid} / {np.name} for {self.kind_label} Execution UUID {self.uuid}")


        logger.info(f"Sent event {event.uuid} to {count} Notification Profiles for {self.kind_label} {self.name} ({self.uuid}) with event")

        return count

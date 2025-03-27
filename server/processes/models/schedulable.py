from datetime import datetime
import logging
import re

from django.db import models

from .named_with_uuid_model import NamedWithUuidModel
from .run_environment import RunEnvironment
from .notification_profile import NotificationProfile
from .event import Event

logger = logging.getLogger(__name__)


class Schedulable(NamedWithUuidModel):
    CRON_REGEX = re.compile(r"cron\s*\(([^)]+)\)")
    RATE_REGEX = re.compile(r"rate\s*\((\d+)\s+([A-Za-z]+)\)")

    class Meta:
        abstract = True

    run_environment = models.ForeignKey(RunEnvironment,
        related_name='+', on_delete=models.CASCADE, blank=True, null=True)

    notification_profiles = models.ManyToManyField(NotificationProfile)

    schedule = models.CharField(max_length=1000, blank=True)
    scheduled_instance_count = models.PositiveIntegerField(null=True,
            blank=True)
    schedule_updated_at = models.DateTimeField(auto_now_add=True)
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
        null=True, blank=True, default=Event.SEVERITY_ERROR)
    notification_event_severity_on_timeout = models.PositiveIntegerField(
        null=True, blank=True, default=Event.SEVERITY_ERROR)
    notification_event_severity_on_missing_execution = models.PositiveIntegerField(
        null=True, blank=True, default=Event.SEVERITY_ERROR)
    notification_event_severity_on_missing_heartbeat = models.PositiveIntegerField(
        null=True, blank=True, default=Event.SEVERITY_WARNING)
    notification_event_severity_on_service_down = models.PositiveIntegerField(
        null=True, blank=True, default=Event.SEVERITY_ERROR)

    def concurrency_at(self, dt: datetime) -> int:
        raise NotImplementedError()


    def send_event_notifications(self, event: Event) -> int:
        #run_env: Optional[RunEnvironment] = None

        #if hasattr(self, 'run_environment'):
        #    run_env = cast(RunEnvironment, self.run_environment)

        run_env = self.run_environment

        notification_profiles = self.notification_profiles.filter(enabled=True)

        # TODO: have a way to specify no notification methods, not falling back to run_env
        if run_env and (not notification_profiles.exists()):
            notification_profiles = run_env.notification_profiles.filter(enabled=True)

        count = 0

        for np in notification_profiles.all():
            # TODO: do these async, retry
            try:
                logger.info(f"Sending notifications for Task {self.uuid} using notification profile {np.uuid} ...")

                np.send(event=event)

                logger.info(f"Done sending notifications for Task {self.uuid} using notification profile {np.uuid}")
                count += 1
            except Exception as ex:
                logger.exception(f"Can't send using Notification Method {np.uuid} / {np.name} for Task Execution UUID {self.uuid}")

        return count

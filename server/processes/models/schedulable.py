from datetime import datetime
import re

from django.db import models

from .named_with_uuid_model import NamedWithUuidModel

class Schedulable(NamedWithUuidModel):
    CRON_REGEX = re.compile(r"cron\s*\(([^)]+)\)")
    RATE_REGEX = re.compile(r"rate\s*\((\d+)\s+([A-Za-z]+)\)")

    class Meta:
        abstract = True

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
    postponed_timeout_before_success_seconds = models.PositiveIntegerField(
        null=True, blank=True)
    max_postponed_timeout_count = models.PositiveIntegerField(null=True,
        blank=True)
    postponed_missing_execution_before_start_seconds = models.PositiveIntegerField(
        null=True, blank=True)
    max_postponed_missing_execution_count = models.PositiveIntegerField(null=True,
        blank=True)
    min_missing_execution_delay_seconds = models.PositiveIntegerField(null=True,
        blank=True)
    should_clear_failure_alerts_on_success = models.BooleanField(default=False)
    should_clear_timeout_alerts_on_success = models.BooleanField(default=False)

    def concurrency_at(self, dt: datetime) -> int:
        raise NotImplementedError()

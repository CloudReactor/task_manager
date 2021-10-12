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


    def concurrency_at(self, dt: datetime) -> int:
        raise NotImplementedError()

from typing import Optional

import enum
import logging

from django.contrib.auth.models import User
from django.db import models

from .schedulable import Schedulable
from .uuid_model import UuidModel
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

    started_at = models.DateTimeField(auto_now_add=True, blank=True)
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

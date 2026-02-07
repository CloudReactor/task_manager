from __future__ import annotations

from typing import TYPE_CHECKING

from datetime import datetime, timedelta
import enum
import logging

from django.db import models
from django.utils import timezone

from .event import Event


if TYPE_CHECKING:
    from .schedulable import Schedulable
    from .execution import Execution

logger = logging.getLogger(__name__)


class ExecutionStatusChangeEvent(Event):
    status = models.IntegerField(null=True, blank=True)
    postponed_until = models.DateTimeField(null=True, blank=True)
    count_with_same_status_after_postponement = models.IntegerField(null=True, blank=True)
    count_with_success_status_after_postponement = models.IntegerField(null=True, blank=True)
    triggered_at = models.DateTimeField(null=True, blank=True)

    def __init__(self, *args, **kwargs):
        from .task_execution import TaskExecution

        super().__init__(*args, **kwargs)

        self.successful_status: enum.IntEnum = TaskExecution.Status.SUCCEEDED
        self.failed_status: enum.IntEnum = TaskExecution.Status.FAILED
        self.terminated_status: enum.IntEnum = TaskExecution.Status.TERMINATED_AFTER_TIME_OUT

    def maybe_postpone(self, schedulable: Schedulable) -> bool:
        should_postpone = False
        if (self.status == self.failed_status) and \
                ((schedulable.max_postponed_failure_count or 0) > 0) and \
                schedulable.postponed_failure_before_success_seconds and \
                (schedulable.postponed_failure_before_success_seconds > 0):
            logger.info(f"ExecutionStatusChangeEvent.maybe_postpone called, postponing failed event {self.uuid}")
            should_postpone = True
            self.postponed_until = timezone.now() + timedelta(seconds=schedulable.postponed_failure_before_success_seconds)
        elif (self.status == self.terminated_status) and \
                ((schedulable.max_postponed_timeout_count or 0) > 0) and \
                schedulable.postponed_timeout_before_success_seconds and \
                (schedulable.postponed_timeout_before_success_seconds > 0):
            logger.info(f"ExecutionStatusChangeEvent.maybe_postpone called, postponing timeout event {self.uuid}")
            should_postpone = True
            self.postponed_until = timezone.now() + timedelta(seconds=schedulable.postponed_timeout_before_success_seconds)
        else:
            logger.info(f"ExecutionStatusChangeEvent.maybe_postpone called but not postponing event {self.uuid}")
            self.triggered_at = timezone.now()

        self.save()

        return should_postpone

    def update_after_postponed(self, status: enum.IntEnum, utc_now: datetime) -> bool:
        if not self.postponed_until:
            logger.info("ExecutionStatusChangeEvent.update_after_postponed called but event not postponed")
            return False

        if self.resolved_at:
            logger.warning("ExecutionStatusChangeEvent.update_after_postponed called but event is already resolved")
            return False

        if self.triggered_at:
            logger.info("ExecutionStatusChangeEvent.update_after_postponed called but event is already triggered")
            return False

        schedulable = self.get_schedulable()

        if schedulable is None:
            logger.warning("ExecutionStatusChangeEvent.update_after_postponed called Schedulable is missing")
        elif not schedulable.enabled:
            logger.info("ExecutionStatusChangeEvent.update_after_postponed called on disabled Schedulable")
        elif status == self.successful_status:
            success_count = (self.count_with_success_status_after_postponement or 0) + 1
            self.count_with_success_status_after_postponement = success_count

            if (schedulable.required_success_count_to_clear_failure is not None) and \
                    (success_count >= schedulable.required_success_count_to_clear_failure):
                logger.info(f"Clearing postponed event {self.uuid} for Task {schedulable.uuid} since success count reached")
                self.resolved_at = utc_now

            self.save()

            return True
        elif status == self.status:
            count_with_same_status = (self.count_with_same_status_after_postponement or 0) + 1
            self.count_with_same_status_after_postponement = count_with_same_status

            threshold_count: int | None = None

            if status == self.failed_status:
                threshold_count = schedulable.max_postponed_failure_count or 0
            elif status == self.terminated_status:
                threshold_count = schedulable.max_postponed_timeout_count or 0

            if (threshold_count is not None) and \
                    (count_with_same_status >= threshold_count):
                logger.info(f"Accelerating postponed event {self.uuid} for Task {schedulable.uuid} since same status count reached")
                self.triggered_at = utc_now
                self.save()

                execution = self.get_execution()
                if execution:
                    execution.send_event_notifications(event=self)

                return True
            else:
                self.save()

        return False

    def get_schedulable(self) -> Schedulable | None:
        execution = self.get_execution()

        if execution is None:
            return None

        return execution.get_schedulable()

    def get_execution(self) -> Execution | None:
        return None

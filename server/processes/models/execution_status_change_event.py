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


class ExecutionStatusChangeEvent:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def maybe_postpone(self, schedulable: Schedulable) -> bool:
        from .execution import Execution

        should_postpone = False
        if (self.status == Execution.Status.FAILED) and \
                ((schedulable.max_postponed_failure_count or 0) > 0) and \
                schedulable.postponed_failure_before_success_seconds and \
                (schedulable.postponed_failure_before_success_seconds > 0):
            logger.info(f"ExecutionStatusChangeEvent.maybe_postpone called, postponing failed event {self.uuid}")
            should_postpone = True
            self.postponed_until = timezone.now() + timedelta(seconds=schedulable.postponed_failure_before_success_seconds)
        elif (self.status == Execution.Status.TERMINATED_AFTER_TIME_OUT) and \
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
        from .execution import Execution


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
        elif status == Execution.Status.SUCCEEDED:
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

            if status == Execution.Status.FAILED:
                threshold_count = schedulable.max_postponed_failure_count or 0
            elif status == Execution.Status.TERMINATED_AFTER_TIME_OUT:
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

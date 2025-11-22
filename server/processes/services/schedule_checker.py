from __future__ import annotations

from typing import Generic, Optional, TypeVar

from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta
import logging

from crontab import CronTab

from dateutil.relativedelta import *

from django.db import transaction
from django.db.models import Manager, Q
from django.utils import timezone

from ..models import MissingScheduledExecutionEvent, Schedulable, Execution
from ..models.schedulable import SCHEDULE_TYPE_CRON, SCHEDULE_TYPE_RATE


MIN_DELAY_BETWEEN_EXPECTED_AND_ACTUAL_SECONDS = 300

logger = logging.getLogger(__name__)


BoundSchedulable = TypeVar('BoundSchedulable', bound=Schedulable)
BoundExecution = TypeVar('BoundExecution', bound=Execution)


class ScheduleChecker(Generic[BoundSchedulable, BoundExecution], metaclass=ABCMeta):
    def check_all(self) -> None:
        model_name = self.model_name()
        for schedulable in self.manager().filter(enabled=True,
                notification_event_severity_on_missing_execution__isnull=False).filter(
                    Q(managed_probability__gte=1.0) |
                    Q(managed_probability__isnull=True)).exclude(schedule='').all():
            logger.info(f"Found {model_name} {schedulable.uuid} with schedule {schedulable.schedule}")
            try:
                self.check_execution_on_time(schedulable)
            except Exception:
                logger.exception(f"check_all() failed on {model_name} {schedulable.uuid}")

    def check_execution_on_time(self, schedulable: BoundSchedulable) \
            -> Optional[MissingScheduledExecutionEvent]:
        schedule = schedulable.schedule.strip()

        if not schedule:
            logger.warning(f"For schedulable entity {schedulable.uuid}, schedule '{schedule}' is blank, skipping")
            return None

        mse: Optional[MissingScheduledExecutionEvent] = None

        utc_now = timezone.now()
        time_range = self.execution_time_range(schedulable, utc_now=utc_now)

        if time_range is None:
            return None

        with transaction.atomic():
            mse = self.check_executions(schedulable, expected_datetime=time_range[0],
                    from_datetime=time_range[1], to_datetime=time_range[2], utc_now=utc_now)

        if mse:
            schedulable.send_event_notifications(event=mse)

        return mse


    @staticmethod
    def execution_time_range(schedulable: BoundSchedulable, utc_now: datetime) \
            -> Optional[tuple[datetime, datetime, datetime]]:
        model_name = schedulable.kind_label
        schedule = schedulable.schedule

        expected_datetime = utc_now
        from_datetime = utc_now
        to_datetime = utc_now
        schedule_updated_at = schedulable.schedule_updated_at

        m = Schedulable.CRON_REGEX.match(schedule)

        if m:
            cron_expr = m.group(1)
            logger.info(
                f"execution_time_range(): {model_name} {schedulable.name} with schedule {schedulable.schedule} has cron expression '{cron_expr}'")

            try:
                entry = CronTab(cron_expr)
            except Exception as ex:
                logger.exception(f"Can't parse cron expression '{cron_expr}'")
                raise ex

            negative_previous_execution_seconds_ago = entry.previous(
                    now=utc_now)

            if negative_previous_execution_seconds_ago is None:
                logger.info('execution_time_range(): No expected previous execution, returning')
                return None

            previous_execution_seconds_ago = -(negative_previous_execution_seconds_ago or 0.0)

            if previous_execution_seconds_ago < MIN_DELAY_BETWEEN_EXPECTED_AND_ACTUAL_SECONDS:
                logger.info('execution_time_range(): Expected previous execution too recent, returning')
                return None

            expected_datetime = utc_now - timedelta(seconds=previous_execution_seconds_ago)
            from_datetime = expected_datetime - timedelta(seconds=Schedulable.DEFAULT_MAX_EARLY_STARTUP_SECONDS)
            to_datetime = expected_datetime + timedelta(seconds=Schedulable.DEFAULT_MAX_SCHEDULED_LATENESS_SECONDS)

            logger.info(
                f"execution_time_range(): Previous execution was supposed to start {previous_execution_seconds_ago / 60} minutes ago at {expected_datetime}")
        else:
            rate_relative_delta = ScheduleChecker.parse_rate_schedule(schedule)

            if rate_relative_delta:
                if schedule_updated_at + rate_relative_delta > utc_now:
                    logger.info(
                        f"execution_time_range(): Next execution after schedule update ({schedule_updated_at}) is in the future, skipping")
                    return None

                from_datetime = utc_now - rate_relative_delta - timedelta(seconds=Schedulable.DEFAULT_MAX_EARLY_STARTUP_SECONDS)
            else:
                raise Exception(f"Schedule '{schedule}' is not a cron or rate expression")


        if expected_datetime < schedulable.schedule_updated_at:
            logger.info(
                f"execution_time_range(): Previous execution expected to start at {from_datetime} but that is before the schedule was last updated at {schedulable.schedule_updated_at}")
            return None

        expected_datetime = (expected_datetime + timedelta(microseconds=500000)).replace(microsecond=0)

        return (expected_datetime, from_datetime, to_datetime)


    def check_executions(self, schedulable: BoundSchedulable, expected_datetime: datetime,
            from_datetime: datetime,
            to_datetime: datetime, utc_now: datetime) -> Optional[MissingScheduledExecutionEvent]:

        model_name = self.model_name()
        executions = schedulable.executions().filter(started_at__gte=from_datetime,
                started_at__lte=to_datetime)
        execution_count = executions.count()
        required_instance_count = max(1, schedulable.scheduled_instance_count or 1)
        missing_execution_count = required_instance_count - execution_count

        event_manager = schedulable.lookup_missing_scheduled_execution_events()

        if schedulable.schedule_type == SCHEDULE_TYPE_CRON:
            event_manager = event_manager.filter(expected_execution_at=expected_datetime)
        elif schedulable.schedule_type == SCHEDULE_TYPE_RATE:
            event_manager = event_manager.order_by('-expected_execution_at')

        mse = event_manager.first()

        if mse:
            if missing_execution_count == mse.missing_execution_count:
                logger.info(
                        f"check_executions(): Found existing matching missing scheduled execution event {mse.uuid} with the same missing execution count of {missing_execution_count}")
                return None
            else:
                logger.info(
                        f"check_executions(): Found existing matching missing scheduled execution event {mse.uuid}, updating execution count")

                mse.missing_execution_count = missing_execution_count

                utc_now = timezone.now()

                if missing_execution_count <= 0:
                    logger.info("check_executions(): marking scheduled execution event as resolved since execution count is now sufficient")
                    mse.resolved_at = utc_now

                mse.save()

                if missing_execution_count <= 0:
                    last_execution = executions.order_by('-started_at').first()
                    resolving_event = schedulable.make_resolved_missing_scheduled_execution_event(
                            detected_at=utc_now,
                            resolved_event=mse,
                            execution=last_execution,
                    )
                    schedulable.send_event_notifications(event=resolving_event)
        else:
            logger.info(
                f"check_executions(): No existing matching missing scheduled execution event found for expected execution at {expected_datetime}")

            if missing_execution_count <= 0:
                logger.info(
                        f"check_executions(): No missing scheduled execution event needed for {model_name} {schedulable.uuid} since execution count is sufficient")
                return None
            else:
                logger.info(
                    f"check_executions(): Only {execution_count} executions of {model_name} {schedulable.uuid}, out of {required_instance_count}, found within the expected time window")

                if schedulable.max_concurrency and \
                        (schedulable.max_concurrency > 0):
                    concurrency = schedulable.concurrency_at(expected_datetime)

                    if concurrency >= schedulable.max_concurrency:
                        logger.info(
                            f"check_executed_at(): {concurrency} concurrent executions of execution of {model_name} {schedulable.uuid} during the expected execution time prevented execution")
                        return None


                logger.info(
                    f"check_executed_at(): creating missing scheduled execution event for {model_name} {schedulable.uuid} since no execution found at expected time {expected_datetime}")

                mse = self.make_missing_scheduled_execution_event(schedulable=schedulable,
                    expected_execution_at=expected_datetime, missing_execution_count=missing_execution_count)
                mse.save()

                return mse

    @staticmethod
    def parse_rate_schedule(schedule: str) -> Optional[relativedelta]:
        m = Schedulable.RATE_REGEX.match(schedule)

        if m:
            n = int(m.group(1))
            time_unit = m.group(2).lower().rstrip('s')
            return ScheduleChecker.make_relative_delta(n, time_unit)

        return None

    @staticmethod
    def make_relative_delta(n: int, time_unit: str) -> relativedelta:
        if time_unit == 'second':
            return relativedelta(seconds=n)
        if time_unit == 'minute':
            return relativedelta(minutes=n)
        if time_unit == 'hour':
            return relativedelta(hours=n)
        if time_unit == 'day':
            return relativedelta(days=n)
        if time_unit == 'month':
            return relativedelta(months=n)
        if time_unit == 'year':
            return relativedelta(years=n)
        raise Exception(f"Unknown time unit '{time_unit}'")

    @abstractmethod
    def model_name(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def manager(self) -> Manager[BoundSchedulable]:
        raise NotImplementedError()

    @abstractmethod
    def make_missing_scheduled_execution_event(self, schedulable: BoundSchedulable,
            expected_execution_at: datetime, missing_execution_count: int) \
            -> MissingScheduledExecutionEvent:
        raise NotImplementedError()

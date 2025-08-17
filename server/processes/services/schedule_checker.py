from __future__ import annotations

from typing import Generic, Optional, TypeVar

from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta
import logging

from crontab import CronTab

from dateutil.relativedelta import *

from django.db import transaction
from django.db.models import Manager
from django.utils import timezone

from ..models import MissingScheduledExecutionEvent, Schedulable, Execution

MIN_DELAY_BETWEEN_EXPECTED_AND_ACTUAL_SECONDS = 300
MAX_EARLY_STARTUP_SECONDS = 60
MAX_STARTUP_SECONDS = 10 * 60
MAX_SCHEDULED_LATENESS_SECONDS = 30 * 60

logger = logging.getLogger(__name__)


BoundSchedulable = TypeVar('BoundSchedulable', bound=Schedulable)
BoundExecution = TypeVar('BoundExecution', bound=Execution)


class ScheduleChecker(Generic[BoundSchedulable, BoundExecution], metaclass=ABCMeta):
    def check_all(self) -> None:
        model_name = self.model_name()
        for schedulable in self.manager().filter(enabled=True,
                notification_event_severity_on_missing_execution__isnull=False).exclude(schedule='').all():
            logger.info(f"Found {model_name} {schedulable.uuid} with schedule {schedulable.schedule}")
            try:
                self.check_execution_on_time(schedulable)
            except Exception:
                logger.exception(f"check_all() failed on {model_name} {schedulable.uuid}")

    def check_execution_on_time(self, schedulable: BoundSchedulable) \
            -> Optional[MissingScheduledExecutionEvent]:
        model_name = self.model_name()
        schedule = schedulable.schedule.strip()

        if not schedule:
            logger.warning(f"For schedulable entity {schedulable.uuid}, schedule '{schedule}' is blank, skipping")
            return None

        mse: Optional[MissingScheduledExecutionEvent] = None

        m = Schedulable.CRON_REGEX.match(schedule)

        if m:
            cron_expr = m.group(1)
            logger.info(
                f"check_execution_on_time(): {model_name} {schedulable.name} with schedule {schedulable.schedule} has cron expression '{cron_expr}'")

            try:
                entry = CronTab(cron_expr)
            except Exception as ex:
                logger.exception(f"Can't parse cron expression '{cron_expr}'")
                raise ex

            utc_now = timezone.now()
            negative_previous_execution_seconds_ago = entry.previous(
                    default_utc=True)

            if negative_previous_execution_seconds_ago is None:
                logger.info('check_execution_on_time(): No expected previous execution, returning')
                return None

            previous_execution_seconds_ago = -(negative_previous_execution_seconds_ago or 0.0)

            if previous_execution_seconds_ago < MIN_DELAY_BETWEEN_EXPECTED_AND_ACTUAL_SECONDS:
                logger.info('check_execution_on_time(): Expected previous execution too recent, returning')
                return None

            early_datetime = (utc_now - timedelta(seconds=previous_execution_seconds_ago) + timedelta(
                microseconds=500000)).replace(microsecond=0)

            if early_datetime < schedulable.schedule_updated_at:
                logger.info(
                    f"check_execution_on_time(): Previous execution expected to start at {early_datetime} but that is before the schedule was last updated at {schedulable.schedule_updated_at}")
                return None

            logger.info(
                f"check_execution_on_time(): Previous execution was supposed to start {previous_execution_seconds_ago / 60} minutes ago at {early_datetime}")

            with transaction.atomic():
                mse = self.check_executed_at(schedulable, early_datetime)
        else:
            m = Schedulable.RATE_REGEX.match(schedule)

            if m:
                n = int(m.group(1))
                time_unit = m.group(2).lower().rstrip('s')

                logger.info(
                    f"{model_name} {schedulable.name} with schedule {schedulable.schedule} has rate of once every {n} {time_unit}s")

                relative_delta = self.make_relative_delta(n, time_unit)
                utc_now = timezone.now()
                early_datetime = (utc_now - relative_delta).replace(second=0, microsecond=0)

                if early_datetime < schedulable.schedule_updated_at:
                    logger.info(
                        f"check_execution_on_time(): Previous execution expected after {early_datetime} but that is before the schedule was last updated at {schedulable.schedule_updated_at}")
                    return None

                logger.info(
                    f"check_execution_on_time(): Previous execution was supposed to start after {early_datetime}")

                with transaction.atomic():
                    mse = self.check_executed_after(schedulable, early_datetime, relative_delta,
                            utc_now)
            else:
                raise Exception(f"Schedule '{schedule}' is not a cron or rate expression")

        if mse:
            schedulable.send_event_notifications(event=mse)

        return mse

    def check_executed_at(self, schedulable: BoundSchedulable,
            expected_datetime: datetime) -> Optional[MissingScheduledExecutionEvent]:
        model_name = self.model_name()
        mse = self.missing_scheduled_executions_of(schedulable).filter(
            expected_execution_at=expected_datetime).first()

        if mse:
            logger.info(
                f"check_executed_at(): Found existing matching missing scheduled execution {mse.uuid}, not creating event")
            return None

        logger.info('check_executed_at(): No existing matching missing scheduled execution found')

        pe = self.executions_of(schedulable).filter(
            started_at__gte=expected_datetime - timedelta(seconds=MAX_EARLY_STARTUP_SECONDS),
            started_at__lte=expected_datetime + timedelta(seconds=MAX_STARTUP_SECONDS)).first()

        if pe:
            logger.info(
                f"check_execution_on_time(): Found execution of {model_name} {schedulable.uuid} within the expected time window")
            return None

        logger.info(
            f"check_executed_at(): No execution of {model_name} {schedulable.uuid} found within the expected time window")

        if schedulable.max_concurrency and \
                (schedulable.max_concurrency > 0):
            concurrency = schedulable.concurrency_at(expected_datetime)

            if concurrency >= schedulable.max_concurrency:
                logger.info(
                    f"check_executed_at(): {concurrency} concurrent executions of execution of {model_name} {schedulable.uuid} during the expected execution time prevented execution")
                return None

        mse = self.make_missing_scheduled_execution_event(schedulable=schedulable,
                expected_execution_at=expected_datetime)
        mse.save()
        return mse

    def check_executed_after(self, schedulable: BoundSchedulable,
            early_datetime: datetime, relative_delta: relativedelta,
            utc_now: datetime):
        model_name = self.model_name()
        mse = self.missing_scheduled_executions_of(schedulable).order_by('-expected_execution_at').first()

        if mse:
            next_expected_execution_at = mse.expected_execution_at + relative_delta
            if next_expected_execution_at >= early_datetime:
                logger.info(
                    f"check_executed_after(): Found existing missing scheduled execution {mse.uuid} expected at {mse.expected_execution_at}, next expected at {next_expected_execution_at}, not creating event")
                return None
        else:
            logger.info(
                f"check_executed_after(): No existing missing scheduled execution events for {model_name} {schedulable.uuid}")

        pe = self.executions_of(schedulable).filter(
            started_at__gte=early_datetime - timedelta(seconds=MAX_EARLY_STARTUP_SECONDS),
            started_at__lte=utc_now).first()

        if pe:
            logger.info(
                f"check_executed_after(): Found execution of {model_name} {schedulable.uuid} at {pe.started_at}, which is after the expected time of {early_datetime}")
            return None

        expected_datetime = utc_now.replace(second=0, microsecond=0)

        logger.info(
            f"check_executed_after(): No execution of {model_name} {schedulable.uuid} found after expected time {expected_datetime}")

        if schedulable.max_concurrency and \
                (schedulable.max_concurrency > 0):

            concurrency = schedulable.concurrency_at(early_datetime)

            if concurrency >= schedulable.max_concurrency:
                logger.info(
                    f"check_executed_after(): {concurrency} concurrent executions of execution of {model_name} {schedulable.uuid} during the expected execution time prevent execution")
                return None

        mse = self.make_missing_scheduled_execution_event(schedulable=schedulable,
                expected_execution_at=expected_datetime)
        mse.save()
        return mse


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
    def missing_scheduled_executions_of(self, schedulable: BoundSchedulable) -> MissingScheduledExecutionEvent:
        raise NotImplementedError()

    @abstractmethod
    def executions_of(self, schedulable: BoundSchedulable) -> Manager[Execution]:
        raise NotImplementedError()

    @abstractmethod
    def make_missing_scheduled_execution_event(self, schedulable: BoundSchedulable,
            expected_execution_at: datetime) -> MissingScheduledExecutionEvent:
        raise NotImplementedError()

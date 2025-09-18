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

        executions = schedulable.executions().filter(
            started_at__gte=expected_datetime - timedelta(seconds=Schedulable.DEFAULT_MAX_EARLY_STARTUP_SECONDS),
            started_at__lte=expected_datetime + timedelta(seconds=Schedulable.DEFAULT_MAX_SCHEDULED_LATENESS_SECONDS))

        execution_count = executions.count()

        required_instance_count = max(1, schedulable.scheduled_instance_count)

        missing_execution_count = required_instance_count - execution_count

        mse = schedulable.lookup_missing_scheduled_execution_events().filter(
            expected_execution_at=expected_datetime).first()

        if mse:
            if missing_execution_count == mse.missing_execution_count:
                logger.info(
                        f"check_executed_at(): Found existing matching missing scheduled execution event {mse.uuid} with the same missing execution count of {missing_execution_count}")
                return None
            else:
                logger.info(
                        f"check_executed_at(): Found existing matching missing scheduled execution event {mse.uuid}, updating execution count")

                mse.missing_execution_count = missing_execution_count

                utc_now = timezone.now()

                if missing_execution_count <= 0:
                    logger.info("check_executed_at(): marking scheduled execution event as resolved since execution count is now sufficient")
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
                f"check_executed_at(): No existing matching missing scheduled execution event found for expected execution at {expected_datetime}")

            if missing_execution_count <= 0:
                logger.info(
                        f"check_executed_at(): No missing scheduled execution event needed for {model_name} {schedulable.uuid} since execution count is sufficient")
                return None
            else:
                logger.info(
                    f"check_executed_at(): Only {execution_count} executions of {model_name} {schedulable.uuid}, out of {required_instance_count}, found within the expected time window")

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

    def check_executed_after(self, schedulable: BoundSchedulable,
            early_datetime: datetime, relative_delta: relativedelta,
            utc_now: datetime):
        model_name = self.model_name()

        from_datetime = early_datetime - timedelta(seconds=Schedulable.DEFAULT_MAX_EARLY_STARTUP_SECONDS)
        to_datetime = utc_now

        executions = schedulable.executions().filter(started_at__gte=from_datetime,
            started_at__lte=to_datetime)

        execution_count = executions.count()

        logger.debug(
            f"check_executed_after(): Found {execution_count} executions of {model_name} {schedulable.uuid} between {from_datetime} and {to_datetime}")

        required_instance_count = max(1, schedulable.scheduled_instance_count)

        missing_execution_count = required_instance_count - execution_count

        mse = schedulable.lookup_missing_scheduled_execution_events().order_by('-expected_execution_at').first()

        # if mse:
        #     next_expected_execution_at = mse.expected_execution_at + relative_delta
        #     if next_expected_execution_at >= early_datetime:
        #         logger.info(
        #             f"check_executed_after(): Found existing missing scheduled execution {mse.uuid} expected at {mse.expected_execution_at}, next expected at {next_expected_execution_at}, ignoring event")
        #         mse = None

        if mse:
            if missing_execution_count == mse.missing_execution_count:
                logger.info(
                        f"check_executed_after(): Found existing matching missing scheduled execution event {mse.uuid} with the same missing execution count of {missing_execution_count}")
                return None
            else:
                logger.info(
                        f"check_executed_after(): Found existing matching missing scheduled execution event {mse.uuid}, updating execution count")

                mse.missing_execution_count = missing_execution_count

                if missing_execution_count <= 0:
                    logger.info("check_executed_after(): marking scheduled execution event as resolved since execution count is now sufficient")
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
                f"check_executed_after(): No existing missing scheduled execution events for {model_name} {schedulable.uuid}")

        if missing_execution_count <= 0:
            logger.info(
                f"check_executed_after(): Found {execution_count} executions of {model_name} {schedulable.uuid} after the expected time of {early_datetime}, which is sufficient")
            return None

        expected_datetime = utc_now.replace(second=0, microsecond=0)

        logger.info(
            f"check_executed_after(): insufficient executions of {model_name} {schedulable.uuid} found after expected time {expected_datetime}, {missing_execution_count=}")

        if schedulable.max_concurrency and \
                (schedulable.max_concurrency > 0):
            concurrency = schedulable.concurrency_at(early_datetime)

            if concurrency >= schedulable.max_concurrency:
                logger.info(
                    f"check_executed_after(): {concurrency} concurrent executions of execution of {model_name} {schedulable.uuid} during the expected execution time prevent execution")
                return None

        logger.info(
            f"check_executed_after(): creating missing scheduled execution event for {model_name} {schedulable.uuid} with {expected_datetime=}, {missing_execution_count=}")

        mse = self.make_missing_scheduled_execution_event(schedulable=schedulable,
                expected_execution_at=expected_datetime, missing_execution_count=missing_execution_count)
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
    def make_missing_scheduled_execution_event(self, schedulable: BoundSchedulable,
            expected_execution_at: datetime, missing_execution_count: int) \
            -> MissingScheduledExecutionEvent:
        raise NotImplementedError()

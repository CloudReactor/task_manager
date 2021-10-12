from abc import ABCMeta, abstractmethod
from datetime import timedelta
import logging

from crontab import CronTab

from dateutil.relativedelta import *

from django.db import transaction
from django.utils import timezone

from processes.common.request_helpers import context_with_request
from processes.models import (
        Alert, AlertSendStatus, AlertMethod,
        Schedulable
)

MIN_DELAY_BETWEEN_EXPECTED_AND_ACTUAL_SECONDS = 300
MAX_EARLY_STARTUP_SECONDS = 60
MAX_STARTUP_SECONDS = 10 * 60
MAX_SCHEDULED_LATENESS_SECONDS = 30 * 60

logger = logging.getLogger(__name__)


class ScheduleChecker(metaclass=ABCMeta):
    def check_all(self):
        model_name = self.model_name()
        for schedulable in self.manager().filter(enabled=True).exclude(schedule='').all():
            logger.info(f"Found {model_name} {schedulable} with schedule {schedulable.schedule}")
            try:
                self.check_execution_on_time(schedulable)
            except Exception:
                logger.exception(f"check_all() failed on {model_name} {schedulable.uuid}")

    def check_execution_on_time(self, schedulable: Schedulable):
        model_name = self.model_name()
        schedule = schedulable.schedule.strip()

        if not schedule:
            logger.warning(f"For schedulable entity {schedulable.uuid}, schedule '{schedule}' is blank, skipping")
            return None

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

            expected_datetime = (utc_now - timedelta(seconds=previous_execution_seconds_ago) + timedelta(
                microseconds=500000)).replace(microsecond=0)

            if expected_datetime < schedulable.schedule_updated_at:
                logger.info(
                    f"check_execution_on_time(): Previous execution expected to start at at {expected_datetime} but that is before the schedule was last updated at {schedulable.schedule_updated_at}")
                return None

            logger.info(
                f"check_execution_on_time(): Previous execution was supposed to start {previous_execution_seconds_ago / 60} minutes ago at {expected_datetime}")

            with transaction.atomic():
                mspe = self.check_executed_at(schedulable, expected_datetime)
        else:
            m = Schedulable.RATE_REGEX.match(schedule)

            if m:
                n = int(m.group(1))
                time_unit = m.group(2).lower().rstrip('s')

                logger.info(
                    f"{model_name} {schedulable.name} with schedule {schedulable.schedule} has rate {n} per {time_unit}")

                relative_delta = self.make_relative_delta(n, time_unit)
                utc_now = timezone.now()
                expected_datetime = utc_now - relative_delta

                if expected_datetime < schedulable.schedule_updated_at:
                    logger.info(
                        f"check_execution_on_time(): Previous execution expected after {expected_datetime} but that is before the schedule was last updated at {schedulable.schedule_updated_at}")
                    return None

                logger.info(
                    f"check_execution_on_time(): Previous execution was supposed to start executed after {expected_datetime}")

                with transaction.atomic():
                    mspe = self.check_executed_after(schedulable,
                        expected_datetime, relative_delta, utc_now)
            else:
                raise Exception(f"Schedule '{schedule}' is not a cron or rate expression")

        if mspe:
            self.send_alerts(mspe)

        return mspe

    def check_executed_at(self, schedulable: Schedulable, expected_datetime):
        model_name = self.model_name()
        mse = self.missing_scheduled_executions_of(schedulable).filter(
            expected_execution_at=expected_datetime).first()

        if mse:
            logger.info(
                f"check_executed_at(): Found existing matching missing scheduled execution {mse.uuid}, not alerting")
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

        mse = self.make_missing_scheduled_execution(schedulable, expected_datetime)
        mse.save()
        return mse

    def check_executed_after(self, schedulable, expected_datetime, relative_delta, utc_now):
        model_name = self.model_name()
        mse = self.missing_scheduled_executions_of(schedulable).order_by('-expected_execution_at').first()

        if mse:
            next_expected_execution_at = mse.expected_execution_at + relative_delta
            if next_expected_execution_at >= expected_datetime:
                logger.info(
                    f"check_executed_after(): Found existing missing scheduled execution {mse.uuid} expected at {mse.expected_execution_at}, next expected at {next_expected_execution_at}, not alerting")
                return None
        else:
            logger.info(
                f"check_executed_after(): No existing missing scheduled execution instances for {model_name} {schedulable.uuid}")

        pe = self.executions_of(schedulable).filter(
            started_at__gte=expected_datetime - timedelta(seconds=MAX_EARLY_STARTUP_SECONDS),
            started_at__lte=utc_now).first()

        if pe:
            logger.info(
                f"check_executed_after(): Found execution of {model_name} {schedulable.uuid} after the expected time")
            return None

        logger.info(
            f"check_executed_after(): No execution of {model_name} {schedulable.uuid} found after expected time")

        if schedulable.max_concurrency and \
                (schedulable.max_concurrency > 0):

            concurrency = schedulable.concurrency_at(expected_datetime)

            if concurrency >= schedulable.max_concurrency:
                logger.info(
                    f"check_executed_after(): {concurrency} concurrent executions of execution of {model_name} {schedulable.uuid} during the expected execution time prevent execution")
                return None

        mse = self.make_missing_scheduled_execution(schedulable, expected_datetime)
        mse.save()
        return mse


    @staticmethod
    def make_relative_delta(n, time_unit) -> relativedelta:
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

    def send_alerts(self, mse):
        details = self.missing_scheduled_execution_to_details(mse, context_with_request())

        for am in mse.schedulable_instance.alert_methods.filter(
                enabled=True).exclude(error_severity_on_missing_execution='').all():
            severity = am.error_severity_on_missing_execution
            mspea = self.make_missing_execution_alert(mse, am)
            mspea.save()

            epoch_minutes = divmod(mse.expected_execution_at.timestamp(), 60)[0]

            grouping_key = f"missing_scheduled_{self.model_name().replace(' ', '_')}-{mse.schedulable_instance.uuid}-{epoch_minutes}"

            try:
                result = am.send(details=details, severity=severity,
                                 summary_template=self.alert_summary_template(),
                                 grouping_key=grouping_key)
                mspea.send_result = result
                mspea.send_status = AlertSendStatus.SUCCEEDED
                mspea.completed_at = timezone.now()
            except Exception as ex:
                logger.exception(f"Failed to send alert for missing execution of {mse.schedulable_instance.uuid}")
                mspea.send_status = AlertSendStatus.FAILED
                mspea.error_message = str(ex)[:Alert.MAX_ERROR_MESSAGE_LENGTH]

            mspea.save()

    @abstractmethod
    def model_name(self):
        pass

    @abstractmethod
    def manager(self):
        pass

    @abstractmethod
    def missing_scheduled_executions_of(self, schedulable: Schedulable):
        pass

    @abstractmethod
    def executions_of(self, schedulable: Schedulable):
        pass

    @abstractmethod
    def make_missing_scheduled_execution(self, schedulable: Schedulable,
            expected_execution_at):
        pass

    @abstractmethod
    def missing_scheduled_execution_to_details(self, mse, context):
        pass

    @abstractmethod
    def make_missing_execution_alert(self, mse, alert_method: AlertMethod):
        pass

    @abstractmethod
    def alert_summary_template(self):
        pass

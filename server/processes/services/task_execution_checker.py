from datetime import timedelta
import logging

from django.db import transaction
from django.utils import timezone

from ..common.request_helpers import context_with_request
from ..models import *
from ..serializers import (
    HeartbeatDetectionEventSerializer,
    DelayedTaskStartDetectionEventSerializer
)

HEARTBEAT_DETECTION_INTERVAL_SECONDS = 60 * 60
MAX_STOPPING_DURATION_SECONDS = 10 * 60

logger = logging.getLogger(__name__)


class TaskExecutionChecker:
    MISSING_HEARTBEAT_EVENT_SUMMARY_TEMPLATE = \
        """Task '{{task_execution.task.name}}' has not sent a heartbeat for more than {{heartbeat_interval_seconds}} seconds after the previous heartbeat at {{last_heartbeat_at}}"""

    DELAYED_TASK_START_EVENT_SUMMARY_TEMPLATE = \
        """Task '{{task_execution.task.name}}' was initiated at {{task_execution.started_at}} but not started yet after {{max_manual_start_delay_before_alert_seconds}} seconds"""

    def check_all(self):
        # TODO: optimize query to only fetch problematic executions
        for te in TaskExecution.objects.select_related(
                'task').filter(status__in=TaskExecution.AWAITING_UPDATE_STATUSES):
            try:
                self.check_task_execution(te)
            except Exception:
                logger.exception(f"Failed checking Task Execution {te.uuid} of Task {te.task}")

    def check_task_execution(self, te: TaskExecution):
        if te.finished_at:
            logger.error(f"Task Execution {te.uuid} has an in progress status but finished_at is not NULL")
            return

        with transaction.atomic():
            te.refresh_from_db()
            if te.status in TaskExecution.AWAITING_UPDATE_STATUSES:
                if not self.check_started_on_time(te):
                    return

                if self.check_timeout(te):
                    return

                if self.check_missing_heartbeat(te):
                    return

    def check_started_on_time(self, te: TaskExecution):
        if te.status != TaskExecution.Status.MANUALLY_STARTED:
            return True

        utc_now = timezone.now()
        run_duration = (utc_now - te.started_at).total_seconds()

        logger.info(f"Task Execution {te.uuid} has been manually started for {run_duration} seconds")

        max_delay_seconds = te.task.max_manual_start_delay_before_alert_seconds
        on_time = True

        if (max_delay_seconds is not None) and (run_duration > max_delay_seconds):
            on_time = False
            logger.info(f"Task Execution {te.uuid} has been manually started for {run_duration} seconds which exceeds the max manual start delay before alert of {max_delay_seconds} seconds")

            existing_dpde = DelayedProcessStartDetectionEvent.objects.filter(
                task_execution=te
            ).first()

            if existing_dpde:
                logger.debug(f"Found existing delayed Task start event {existing_dpde.uuid}, not creating another")
            else:
                expected_started_before = (te.started_at + timedelta(seconds=max_delay_seconds)).replace(microsecond=0)
                dpsde = DelayedProcessStartDetectionEvent(task_execution=te,
                                                          resolved_at=None,
                                                          expected_started_before=expected_started_before)
                dpsde.save()
                self.send_delayed_task_start_alerts(dpsde)

        max_delay_seconds = te.task.max_manual_start_delay_before_abandonment_seconds

        if (max_delay_seconds is not None) and (run_duration > max_delay_seconds):
            on_time = False
            logger.info(f"Task Execution {te.uuid} has been manually started for {run_duration} seconds which exceeds the max manual start delay before abandonment of {max_delay_seconds} seconds")
            te.status = TaskExecution.Status.ABANDONED
            te.stop_reason = TaskExecution.StopReason.FAILED_TO_START
            te.marked_done_at = utc_now
            te.save()

        return on_time

    def check_timeout(self, te: TaskExecution):
        task = te.task
        utc_now = timezone.now()
        run_duration = (utc_now - (te.started_at or te.created_at)).total_seconds()
        logger.info(f"Run duration of Task Execution {te.uuid} is {run_duration} seconds")

        if te.status == TaskExecution.Status.STOPPING:
            if run_duration >= MAX_STOPPING_DURATION_SECONDS:
                logger.info(
                    f"Run duration of Task Execution {te.uuid} {run_duration} seconds > max stopping duration {task.max_age_seconds} seconds, abandoning")
                te.status = TaskExecution.Status.ABANDONED
                te.marked_done_at = utc_now
                te.finished_at = utc_now
                te.save()
                return True
        elif task.max_age_seconds is not None:
            if run_duration > task.max_age_seconds:
                logger.info(
                    f"Run duration of Task Execution {te.uuid} {run_duration} seconds > max age {task.max_age_seconds} seconds, stopping")
                te.status = TaskExecution.Status.STOPPING
                te.marked_done_at = utc_now
                te.stop_reason = TaskExecution.StopReason.MAX_EXECUTION_TIME_EXCEEDED
                # This will send alerts if configured by the Task
                te.save()
                return True

            logger.debug(f"Run duration of Task Execution {te.uuid} is within max age")

        return False

    def check_missing_heartbeat(self, te: TaskExecution):
        if te.status != TaskExecution.Status.RUNNING:
            logger.debug(f"Task Execution {te.uuid} is not running, not checking heartbeats")
            return False

        task = te.task
        is_missing = False

        heartbeat_interval_seconds = te.heartbeat_interval_seconds
        if (heartbeat_interval_seconds is not None) and te.started_at:
            utc_now = timezone.now()
            last_heartbeat_at = te.last_heartbeat_at or te.started_at
            last_heartbeat_seconds_ago = (utc_now - last_heartbeat_at).total_seconds()

            heartbeat_interval_timedelta = timedelta(
                seconds=heartbeat_interval_seconds)
            if task.aws_ecs_service_updated_at and (
                    task.aws_ecs_service_updated_at > last_heartbeat_at):
                expected_heartbeat_at = task.aws_ecs_service_updated_at + heartbeat_interval_timedelta
            else:
                expected_heartbeat_at = last_heartbeat_at + heartbeat_interval_timedelta

            logger.info(
                f"Last heartbeat of Task Execution {te.uuid} was {last_heartbeat_seconds_ago} seconds ago, interval = {heartbeat_interval_seconds}, expected heartbeat at {expected_heartbeat_at}")

            # Don't alert on missing heartbeats on processes started before the service was updated
            alert_eligible = (task.aws_ecs_service_updated_at is None) or \
                     (te.started_at > task.aws_ecs_service_updated_at)

            if (task.max_heartbeat_lateness_before_abandonment_seconds is not None) and \
                    (last_heartbeat_seconds_ago > heartbeat_interval_seconds + task.max_heartbeat_lateness_before_abandonment_seconds) and \
                    (expected_heartbeat_at + timedelta(seconds=task.max_heartbeat_lateness_before_abandonment_seconds) < utc_now):
                logger.info(f"Last heartbeat of Task Execution {te.uuid} was {last_heartbeat_seconds_ago} seconds ago > max = {task.max_heartbeat_lateness_before_abandonment_seconds}")
                te.status = TaskExecution.Status.ABANDONED
                te.stop_reason = TaskExecution.StopReason.MISSING_HEARTBEAT
                te.marked_done_at = utc_now
                te.finished_at = utc_now
                te.skip_alert = not alert_eligible
                te.save()
                is_missing = True
            elif (task.max_heartbeat_lateness_before_alert_seconds is not None) and \
                    (last_heartbeat_seconds_ago > heartbeat_interval_seconds + task.max_heartbeat_lateness_before_alert_seconds) and \
                    (expected_heartbeat_at + timedelta(
                        seconds=task.max_heartbeat_lateness_before_alert_seconds) < utc_now) and \
                    alert_eligible:
                is_missing = True
                logger.info(f"Last heartbeat of Task Execution {te.uuid}: missing heartbeat eligible for warning")

                last_heartbeat_detection_event = HeartbeatDetectionEvent.objects.filter(
                    task_execution=te).order_by('-detected_at', '-id').first()

                if (not last_heartbeat_detection_event) or \
                        last_heartbeat_detection_event.resolved_at or \
                        (last_heartbeat_detection_event.detected_at - utc_now).total_seconds() > HEARTBEAT_DETECTION_INTERVAL_SECONDS:
                    logger.info(f"Saving missing heartbeat detection event for Task Execution {te.uuid}")
                    hde = HeartbeatDetectionEvent(
                        task_execution=te,
                        resolved_at=None,
                        last_heartbeat_at=last_heartbeat_at.replace(microsecond=0),
                        expected_heartbeat_at=expected_heartbeat_at.replace(microsecond=0),
                        heartbeat_interval_seconds=heartbeat_interval_seconds)
                    hde.save()
                    self.send_heartbeat_detection_alerts(hde)
                else:
                    logger.debug(f"Found existing last heartbeat detection event for Task Execution {te.uuid}")
            else:
                logger.debug(f'Not abandoning or sending alert for Task Execution {te.uuid} with {task.max_heartbeat_lateness_before_alert_seconds=}')

        return is_missing

    def send_heartbeat_detection_alerts(self, hde: HeartbeatDetectionEvent):
        te = hde.task_execution
        details = HeartbeatDetectionEventSerializer(hde,
            context=context_with_request()).data

        if te.last_heartbeat_at and details['task_execution']['last_heartbeat_at']:
            details['task_execution']['last_heartbeat_at'] = \
                te.last_heartbeat_at.replace(microsecond=0).isoformat()

        for am in te.task.alert_methods.filter(
                enabled=True).exclude(error_severity_on_missing_heartbeat='').all():
            severity = am.error_severity_on_missing_heartbeat
            mha = HeartbeatDetectionAlert(heartbeat_detection_event=hde,
                                          alert_method=am)
            mha.save()

            try:
                # task_execution is already in details
                result = am.send(details=details, severity=severity,
                                 summary_template=self.MISSING_HEARTBEAT_EVENT_SUMMARY_TEMPLATE,
                                 grouping_key=f"missing_heartbeat-{te.uuid}")
                mha.send_result = result
                mha.send_status = AlertSendStatus.SUCCEEDED
                mha.completed_at = timezone.now()
            except Exception as ex:
                logger.exception(f"Failed to send alert for missing heartbeat of Task Execution {hde.task_execution.uuid}")
                mha.send_result = ''
                mha.send_status = AlertSendStatus.FAILED
                mha.error_message = str(ex)[:Alert.MAX_ERROR_MESSAGE_LENGTH]

            mha.save()

    def send_delayed_task_start_alerts(self,
            dpsde: DelayedProcessStartDetectionEvent):
        details = DelayedTaskStartDetectionEventSerializer(dpsde,
            context=context_with_request()).data

        te = dpsde.task_execution

        if details['task_execution']['started_at']:
            details['task_execution']['started_at'] = \
                te.started_at.replace(microsecond=0).isoformat()

        details['max_manual_start_delay_before_alert_seconds'] = te.task.max_manual_start_delay_before_alert_seconds

        for am in te.task.alert_methods.filter(
                enabled=True).exclude(error_severity_on_missing_execution='').all():
            severity = am.error_severity_on_missing_execution
            dpsa = DelayedProcessStartAlert(delayed_process_start_detection_event=dpsde,
                                            alert_method=am)
            dpsa.save()

            try:
                # task_execution is already in details
                result = am.send(details=details, severity=severity,
                        summary_template=self.DELAYED_TASK_START_EVENT_SUMMARY_TEMPLATE,
                        grouping_key=f"delayed_task_start-{te.uuid}")
                dpsa.send_result = result
                dpsa.send_status = AlertSendStatus.SUCCEEDED
                dpsa.completed_at = timezone.now()
            except Exception as ex:
                logger.exception(
                    f"Failed to send alert for missing heartbeat of Task Execution {dpsde.task_execution.uuid}")
                dpsa.send_result = ''
                dpsa.send_status = AlertSendStatus.FAILED
                dpsa.error_message = str(ex)[:Alert.MAX_ERROR_MESSAGE_LENGTH]

            dpsa.save()

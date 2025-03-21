from typing import cast, Optional, Type, TYPE_CHECKING

import enum
import json
import logging

from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from django.contrib.postgres.fields import ArrayField
from django.utils import timezone

from django_middleware_global_request.middleware import get_request

from rest_framework.exceptions import ValidationError

from ..common.aws import *
from ..common.request_helpers import context_with_request
from ..common.pagerduty import *
from ..common.utils import coalesce
from ..execution_methods import ExecutionMethod

from .execution import Execution
from .task import Task
from .event import Event
from .alert_send_status import AlertSendStatus
from .task_execution_configuration import TaskExecutionConfiguration
from .schedulable import Schedulable
from .aws_tagged_entity import AwsTaggedEntity


if TYPE_CHECKING:
    from .task_execution_status_change_event import (
        TaskExecutionStatusChangeEvent
    )
    from .missing_heartbeat_detection_event import MissingHeartbeatDetectionEvent


logger = logging.getLogger(__name__)


class TaskExecution(TaskExecutionConfiguration, AwsTaggedEntity, Execution):
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

    @enum.unique
    class StopReason(enum.IntEnum):
        MANUAL = 0
        MAX_EXECUTION_TIME_EXCEEDED = 1
        MISSING_HEARTBEAT = 2
        FAILED_TO_START = 3
        WORKFLOW_EXECUTION_STOPPED = 100
        WORKFLOW_EXECUTION_RETRIED = 101
        WORKFLOW_EXECUTION_TIMED_OUT = 102

    IN_PROGRESS_STATUSES = [Status.MANUALLY_STARTED, Status.RUNNING]
    UNSUCCESSFUL_STATUSES = [
        Status.FAILED, Status.TERMINATED_AFTER_TIME_OUT, Status.MARKED_DONE,
        Status.EXITED_AFTER_MARKED_DONE, Status.STOPPING, Status.STOPPED,
        Status.ABANDONED, Status.ABORTED
    ]
    COMPLETED_STATUSES = [Status.SUCCEEDED] + UNSUCCESSFUL_STATUSES
    AWAITING_UPDATE_STATUSES = IN_PROGRESS_STATUSES + [Status.STOPPING]

    FOUND_HEARTBEAT_EVENT_SUMMARY_TEMPLATE = \
        """Task '{{task_execution.task.name}}' has sent a heartbeat after being late"""
    CLEARED_DELAYED_PROCESS_START_EVENT_SUMMARY_TEMPLATE = \
        """Task '{{task_execution.task.name}}' has started after being manually started and being late to start"""
    FOUND_SCHEDULED_EXECUTION_SUMMARY_TEMPLATE = \
        """Task '{{task.name}}' has started after being late according to its schedule"""

    UNMODIFIABLE_ATTRIBUTES = [
        'started_at', 'started_by', 'finished_at',
        'kill_started_at', 'kill_finished_at', 'kill_error_code', 'killed_by',
        'marked_outdated_at', 'marked_done_at', 'marked_done_by',]

    MERGED_ATTRIBUTES = [
        'infrastructure_settings', 'execution_method_details',
        'other_runtime_metadata'
    ]

    ATTRIBUTES_REQUIRING_DEVELOPER_ACCESS_FOR_UPDATE = [
        'process_command',
        'task_max_concurrency',
        'prevent_offline_execution',
        'api_base_url', 'api_key',
        'api_request_timeout_seconds',
        'api_retry_delay_seconds',
        'api_resume_delay_seconds',
        'api_error_timeout_seconds',
        'api_task_execution_creation_error_timeout_seconds',
        'api_task_execution_creation_conflict_timeout_seconds',
        'api_task_execution_creation_conflict_retry_delay_seconds',
        'api_final_update_timeout_seconds',
    ]

    # Do not send alerts for Task Executions that finished more than one day
    # ago.
    MAX_STATUS_ALERT_AGE_SECONDS = 24 * 60 * 60

    task = models.ForeignKey(Task, on_delete=models.CASCADE,
            db_column='process_type_id')
    auto_created_task_properties = models.JSONField(null=True, blank=True)
    task_version_number = models.BigIntegerField(null=True, blank=True,
            db_column='process_version_number')
    task_version_signature = models.CharField(max_length=200, null=True, blank=True,
            db_column='process_version_signature')
    task_version_text = models.CharField(max_length=200, null=True, blank=True,
            db_column='process_version_text')
    heartbeat_interval_seconds = models.IntegerField(null=True, blank=True)
    hostname = models.CharField(max_length=1000, null=True, blank=True)

    last_app_heartbeat_at = models.DateTimeField(null=True, blank=True)
    exit_code = models.IntegerField(null=True, blank=True)

    debug_log_tail = models.CharField(max_length=5000000, null=True, blank=True)
    error_log_tail = models.CharField(max_length=5000000, null=True, blank=True)
    last_status_message = models.CharField(max_length=5000, null=True, blank=True)
    success_count = models.BigIntegerField(null=True, blank=True)
    error_count = models.BigIntegerField(null=True, blank=True)
    skipped_count = models.BigIntegerField(null=True, blank=True)
    expected_count = models.BigIntegerField(null=True, blank=True)

    current_cpu_units = models.PositiveIntegerField(null=True, blank=True)
    mean_cpu_units = models.PositiveIntegerField(null=True, blank=True)
    max_cpu_units = models.IntegerField(null=True, blank=True)
    current_memory_mb = models.PositiveIntegerField(null=True, blank=True)
    mean_memory_mb = models.PositiveIntegerField(null=True, blank=True)
    max_memory_mb = models.IntegerField(null=True, blank=True)
    wrapper_version = models.CharField(max_length=200, null=True, blank=True)

    # These are sent back from the wrapper, can be overridden when starting
    # an execution.
    wrapper_log_level = models.CharField(max_length=20, null=True)
    deployment = models.CharField(max_length=200, null=True)
    is_service = models.BooleanField(null=True, blank=True)
    task_max_concurrency = models.IntegerField(null=True, blank=True,
            db_column='process_max_concurrency')
    max_conflicting_age_seconds = models.IntegerField(null=True, blank=True)

    # Deprecated
    schedule = models.CharField(max_length=1000, null=True, blank=True)

    api_base_url = models.CharField(max_length=200, blank=True)
    api_key = models.CharField(max_length=40, blank=True)

    # Deprecated for wrappers < 2.0
    api_max_retries = models.IntegerField(null=True, blank=True)
    # Deprecated for wrappers < 2.0
    api_max_retries_for_final_update = models.IntegerField(null=True, blank=True)
    # Deprecated for wrappers < 2.0
    api_max_retries_for_process_creation_conflict = models.IntegerField(null=True, blank=True)

    embedded_mode = models.BooleanField(null=True, blank=True)

    execution_method_type = models.CharField(max_length=100, null=False,
            blank=True, default='')
    execution_method_details = models.JSONField(null=True, blank=True)

    build_task_execution = models.ForeignKey(
      'TaskExecution', on_delete=models.DO_NOTHING,
      to_field='uuid', db_column='build_task_execution_uuid',
      blank=True, null=True,  related_name='+', db_constraint=False
    )

    deployment_task_execution = models.ForeignKey(
      'TaskExecution', on_delete=models.DO_NOTHING,
      to_field='uuid', db_column='deployment_task_execution_uuid',
      blank=True, null=True,  related_name='+', db_constraint=False
    )

    # Deprecated
    aws_subnets = ArrayField(models.CharField(max_length=1000, blank=False), null=True)
    aws_ecs_task_definition_arn = models.CharField(max_length=1000, blank=True)
    aws_ecs_task_arn = models.CharField(max_length=1000, blank=True)
    aws_ecs_launch_type = models.CharField(max_length=50, blank=True)
    aws_ecs_cluster_arn = models.CharField(max_length=1000, blank=True)
    aws_ecs_security_groups = ArrayField(models.CharField(max_length=1000, blank=False), null=True)
    aws_ecs_assign_public_ip = models.BooleanField(null=True)
    aws_ecs_execution_role = models.CharField(max_length=1000, blank=True)
    aws_ecs_task_role = models.CharField(max_length=1000, blank=True)
    aws_ecs_platform_version = models.CharField(max_length=10, blank=True)

    # Transient properties
    skip_alert = False

    class Meta:
        db_table = 'processes_processexecution'
        ordering = ['started_at']

    def __str__(self) -> str:
        return self.task.name + ' / ' + str(self.uuid)

    def get_schedulable(self) -> Optional[Schedulable]:
        return self.task

    @property
    def dashboard_path(self) -> str:
        return 'task_executions'

    def is_in_progress(self) -> bool:
        return self.status in TaskExecution.IN_PROGRESS_STATUSES

    def is_successful(self) -> bool:
        return self.status == TaskExecution.Status.SUCCEEDED

    # FIXME: this works for GitHub and GitLab, not sure about other providers
    @property
    def commit_url(self) -> Optional[str]:
        if self.task.project_url and self.task_version_signature:
            return self.task.project_url.rstrip('/') + '/commit/' + self.task_version_signature
        return None

    def manually_start(self) -> None:
        logger.info("TaskExecution.manually_start()")

        if self.status != TaskExecution.Status.MANUALLY_STARTED:
            raise ValidationError(
                    detail=f"Task execution has status {self.status}, can't manually start")

        if self.task.passive:
            raise ValidationError(detail="Can't manually start a passive Task")

        exec_method = self.execution_method()

        logger.info(f"{exec_method=}, cap = {exec_method.capabilities()}")

        if ExecutionMethod.ExecutionCapability.MANUAL_START not in exec_method.capabilities():
            raise ValidationError(detail="Execution method does not support manual start")

        exec_method.manually_start()

    def enrich_settings(self) -> None:
        self.execution_method().enrich_task_execution_settings()

    def execution_method(self) -> ExecutionMethod:
        return ExecutionMethod.make_execution_method(task_execution=self)

    def make_environment(self, include_wrapper_vars: bool = True, include_app_vars: bool = True) -> dict[str, str]:
        task = self.task

        env: dict[str, str] = {}

        if include_wrapper_vars:
            deployment = self.deployment

            if (not deployment) and task.run_environment:
                deployment = task.run_environment.name

            env = {
                'PROC_WRAPPER_TASK_EXECUTION_UUID': str(self.uuid),
                'PROC_WRAPPER_TASK_NAME': task.name,
                'PROC_WRAPPER_INPUT_VALUE': json.dumps(
                    coalesce(self.input_value, task.default_input_value)),
                'PROC_WRAPPER_MANAGED_PROBABILITY': str(task.managed_probability),
                'PROC_WRAPPER_FAILURE_REPORT_PROBABILITY': str(task.failure_report_probability),
                'PROC_WRAPPER_TIMEOUT_REPORT_PROBABILITY': str(task.timeout_report_probability)
            }

            if deployment:
                env['PROC_WRAPPER_DEPLOYMENT'] = deployment

            if self.wrapper_log_level:
                env['PROC_WRAPPER_LOG_LEVEL'] = self.wrapper_log_level

            if self.process_command:
                env['PROC_WRAPPER_TASK_COMMAND'] = self.process_command

            if self.is_service is not None:
                env['PROC_WRAPPER_TASK_IS_SERVICE'] = str(self.is_service).upper()

            if self.process_max_retries is not None:
                env['PROC_WRAPPER_PROCESS_MAX_RETRIES'] = str(self.process_max_retries)

            if self.process_retry_delay_seconds:
                env['PROC_WRAPPER_PROCESS_RETRY_DELAY_SECONDS'] = str(self.process_retry_delay_seconds)

            if self.process_timeout_seconds:
                env['PROC_WRAPPER_PROCESS_TIMEOUT_SECONDS'] = str(self.process_timeout_seconds)

            if self.process_termination_grace_period_seconds:
                env[' PROC_WRAPPER_PROCESS_TERMINATION_GRACE_PERIOD_SECONDS'] = \
                          str(self.process_termination_grace_period_seconds)

            if self.task_max_concurrency:
                env['PROC_WRAPPER_TASK_MAX_CONCURRENCY'] = str(self.task_max_concurrency)

            if self.max_conflicting_age_seconds:
                env['PROC_WRAPPER_MAX_CONFLICTING_AGE_SECONDS'] = str(self.max_conflicting_age_seconds)

            if self.prevent_offline_execution is not None:
                env['PROC_WRAPPER_PREVENT_OFFLINE_EXECUTION'] = \
                        str(self.prevent_offline_execution).upper()

            if self.api_key:
                env['PROC_WRAPPER_API_KEY'] = self.api_key

            heartbeat_interval_seconds = self.heartbeat_interval_seconds or \
                task.heartbeat_interval_seconds
            if heartbeat_interval_seconds is not None:
                env['PROC_WRAPPER_API_HEARTBEAT_INTERVAL_SECONDS'] = str(heartbeat_interval_seconds)

            if self.api_request_timeout_seconds is not None:
                env['PROC_WRAPPER_API_REQUEST_TIMEOUT_SECONDS'] = \
                        str(self.api_request_timeout_seconds)

            if self.api_retry_delay_seconds is not None:
                env['PROC_WRAPPER_API_RETRY_DELAY_SECONDS'] = \
                        str(self.api_retry_delay_seconds)

            if self.api_resume_delay_seconds is not None:
                env['PROC_WRAPPER_API_RETRY_DELAY_SECONDS'] = \
                        str(self.api_resume_delay_seconds)

            if self.api_error_timeout_seconds is not None:
                env['PROC_WRAPPER_API_ERROR_TIMEOUT_SECONDS'] = \
                        str(self.api_error_timeout_seconds)

            if self.api_task_execution_creation_error_timeout_seconds is not None:
                env['PROC_WRAPPER_API_TASK_EXECUTION_CREATION_ERROR_TIMEOUT_SECONDS'] = \
                        str(self.api_task_execution_creation_error_timeout_seconds)

            if self.api_task_execution_creation_conflict_timeout_seconds is not None:
                env['PROC_WRAPPER_API_TASK_EXECUTION_CREATION_CONFLICT_TIMEOUT_SECONDS'] = \
                        str(self.api_task_execution_creation_conflict_timeout_seconds)

            if self.api_task_execution_creation_conflict_retry_delay_seconds is not None:
                env['PROC_WRAPPER_API_TASK_EXECUTION_CREATION_CONFLICT_RETRY_DELAY_SECONDS'] = \
                        str(self.api_task_execution_creation_conflict_retry_delay_seconds)

            if self.api_final_update_timeout_seconds is not None:
                env['PROC_WRAPPER_API_FINAL_UPDATE_TIMEOUT_SECONDS'] = \
                        str(self.api_final_update_timeout_seconds)

            if self.api_max_retries_for_final_update is not None:
                env['PROC_WRAPPER_API_RETRIES_FOR_FINAL_UPDATE'] = \
                        str(self.api_max_retries_for_final_update)

            if self.api_max_retries_for_process_creation_conflict is not None:
                env['PROC_WRAPPER_API_RETRIES_FOR_PROCESS_CREATION_CONFLICT'] = \
                        str(self.api_max_retries_for_process_creation_conflict)

            if self.status_update_port is not None:
                env['PROC_WRAPPER_ENABLE_STATUS_UPDATE_LISTENER'] = \
                        str(self.status_update_port >= 0).upper()

            if self.status_update_interval_seconds is not None:
                env['PROC_WRAPPER_STATUS_UPDATE_INTERVAL_SECONDS'] = \
                        str(self.status_update_interval_seconds)

            if self.status_update_port is not None:
                env['PROC_WRAPPER_STATUS_UPDATE_PORT'] = \
                        str(self.status_update_port)

            if self.status_update_message_max_bytes is not None:
                env['PROC_WRAPPER_STATUS_UPDATE_MESSAGE_MAX_BYTES'] = \
                        str(self.status_update_message_max_bytes)

            # Legacy: remove once wrappers < 2.0.0 are extinct
            env['PROC_WRAPPER_PROCESS_EXECUTION_UUID'] = env['PROC_WRAPPER_TASK_EXECUTION_UUID']
            env['PROC_WRAPPER_PROCESS_TYPE_NAME'] = env['PROC_WRAPPER_TASK_NAME']

            if self.is_service is not None:
                env['PROC_WRAPPER_PROCESS_IS_SERVICE'] = str(self.is_service).upper()

            if self.task_max_concurrency:
                env['PROC_WRAPPER_PROCESS_MAX_CONCURRENCY'] = str(self.task_max_concurrency)
            # End Legacy

        if include_app_vars:
            for overrides in [
                task.environment_variables_overrides,
                self.environment_variables_overrides]:
                if overrides is not None:
                    for name, value in overrides.items():
                        if value is None:
                            env.pop(name, None)
                        elif isinstance(value, bool):
                            env[name] = str(value).upper()
                        else:
                            env[name] = str(value)
        return env

    def should_create_status_change_event(self) -> bool:
        from .task_execution_status_change_event import TaskExecutionStatusChangeEvent

        if self.skip_alert:
            logger.info("Skipping status change event creation since skip_alert = True")
            return False

        task = self.task

        if not task:
            logger.info("Skipping status change event creation since Task is missing")
            return False

        if not task.enabled:
            logger.info(f"Skipping status change event creation since Task {task.uuid} is disabled")
            return False

        if self.status == TaskExecution.Status.ABORTED:
            # TODO: keep track of service updated_at for generic services
            if task.aws_ecs_service_updated_at and \
                    (task.aws_ecs_service_updated_at > self.started_at):
                logger.info(f"Skipping status change event creation for Task Execution {self.uuid} started after service updated")
                return False

        if TaskExecutionStatusChangeEvent.objects.filter(task_execution=self, status=self.status).exists():
            logger.info(f"Skipping status change event creation for Task Execution {self.uuid} since it already has a status change event")
            return False

        return True


    def update_postponed_events(self) -> int:
        from .task_execution_status_change_event import TaskExecutionStatusChangeEvent

        task = self.task

        if not task:
            logger.warning("Skipping updating postponed notifications since Task is missing")
            return 0

        if not task.enabled:
            logger.info("Skipping updating postponed notifications since Task is disabled")
            return 0


        status = self.status
        utc_now = timezone.now()
        events = TaskExecutionStatusChangeEvent.objects.filter(task=self.task,
                postponed_until__isnull=False, postponed_until__gt=utc_now,
                resolved_at__isnull=True, triggered_at__isnull=True)

        if not events.exists():
            return 0

        updated_count = 0

        for event in events.all():
            if event.update_after_postponed(status=status, utc_now=utc_now):
                updated_count += 1

        return updated_count

    def maybe_create_and_send_status_change_event(self) -> Optional['TaskExecutionStatusChangeEvent']:
        from .task_execution_status_change_event import TaskExecutionStatusChangeEvent

        if self.skip_alert:
            logger.info("Skipping status change event creation since skip_alert = True")
            return None

        task = self.task

        if task is None:
            logger.info("Skipping status change event creation since Task is missing")
            return None

        if not task.enabled:
            logger.info(f"Skipping status change event creation since Task {task.uuid} is disabled")
            return None

        utc_now = timezone.now()

        if self.finished_at and \
            ((utc_now - self.finished_at).total_seconds() > self.MAX_STATUS_ALERT_AGE_SECONDS):
            logger.info(f"Skipping status change event creation since finished_at={self.finished_at} is too long ago")
            return None

        if not self.should_create_status_change_event():
            logger.info(f"Skipping status change event creation since Task {task.uuid} should not create status change event")
            return None

        severity: Optional[int] = TaskExecutionStatusChangeEvent.SEVERITY_ERROR

        if self.status == TaskExecution.Status.SUCCEEDED:
            severity = task.notification_event_severity_on_success
        elif self.status == TaskExecution.Status.FAILED:
            severity = task.notification_event_severity_on_failure
        elif self.status == TaskExecution.Status.TERMINATED_AFTER_TIME_OUT:
            severity = task.notification_event_severity_on_timeout

        # TODO: default to Run Environment's severities, override with TaskExecution severities

        if (severity is None) or (severity == TaskExecutionStatusChangeEvent.SEVERITY_NONE):
            logger.info(f"Skipping notifications since Task {task.uuid} has no severity set for status {self.status}")
            return None

        status_change_event = TaskExecutionStatusChangeEvent(
            severity=severity,
            task=self.task,
            task_execution=self,
            status=self.status,
            details={

            },
            count_with_same_status_after_postponement=0,
            count_with_success_status_after_postponement=0
        )

        status_change_event.save()

        if status_change_event.maybe_postpone(schedulable=task):
            logger.info(f"Postponing notifications on Task {task.uuid} after execution status = {self.status}")
        else:
            logger.info(f"Not postponing notifications on Task {task.uuid} after execution status = {self.status}")
            self.send_event_notifications(event=status_change_event)

        return status_change_event

    def send_event_notifications(self, event: Event) -> int:

        task = self.task

        if task is None:
            logger.warning("Skipping sending notifications since Task is missing")
            return 0

        return task.send_event_notifications(event=event)

    def clear_missing_scheduled_execution_alerts(self, mspe):
        from .alert import Alert
        from .missing_scheduled_task_execution_alert import MissingScheduledTaskExecutionAlert
        from processes.serializers import MissingScheduledTaskExecutionSerializer

        details = MissingScheduledTaskExecutionSerializer(mspe,
                context=context_with_request()).data

        for am in self.task.alert_methods.filter(
                enabled=True).exclude(error_severity_on_missing_execution='').all():
            mha = MissingScheduledTaskExecutionAlert(
                    missing_scheduled_task_execution=mspe,
                    alert_method=am)
            mha.save()

            try:
                # task is already in details
                epoch_minutes = divmod(mspe.expected_execution_at.timestamp(), 60)[0]

                # FIXME: wrong signature
                result = am.send(details=details,
                        summary_template=self.FOUND_SCHEDULED_EXECUTION_SUMMARY_TEMPLATE,
                        grouping_key=f"missing_scheduled_task-{self.task.uuid}-{epoch_minutes}",
                        is_resolution=True)
                mha.send_result = result
                mha.send_status = AlertSendStatus.SUCCEEDED
                mha.completed_at = timezone.now()
            except Exception as ex:
                logger.exception(
                    f"Failed to clear alert for missing scheduled execution of Task {mspe.task.uuid}")
                mha.send_result = ''
                mha.send_status = AlertSendStatus.FAILED
                mha.error_message = str(ex)[:Alert.MAX_ERROR_MESSAGE_LENGTH]

            mha.save()

    def send_resolved_missing_heartbeat_detection_notifications(self, hde: 'MissingHeartbeatDetectionEvent'):
        for np in self.task.notification_profiles.filter(enabled=True).all():
            try:
                np.send(event=hde)
            except Exception as ex:
                te_id = str(hde.task_execution.uuid) if hde.task_execution else '[REMOVED]'
                logger.exception(
                    f"Failed to clear alert for missing heartbeat of Task Execution {te_id}")

    def clear_delayed_task_start_alerts(self, dpsde):
        from .alert import Alert
        from .delayed_process_start_alert import DelayedProcessStartAlert
        from processes.serializers import DelayedTaskStartDetectionEventSerializer

        details = DelayedTaskStartDetectionEventSerializer(dpsde,
            context=context_with_request()).data

        details['max_manual_start_delay_before_alert_seconds'] = self.task.max_manual_start_delay_before_alert_seconds

        for am in self.task.alert_methods.filter(
                enabled=True).exclude(error_severity_on_missing_execution='').all():
            dpsa = DelayedProcessStartAlert(delayed_process_start_detection_event=dpsde,
                                            alert_method=am)
            dpsa.save()

            try:
                # task_execution is already in details
                result = am.send(details=details,
                                 summary_template=self.CLEARED_DELAYED_PROCESS_START_EVENT_SUMMARY_TEMPLATE,
                                 grouping_key=f"delayed_task_start-{self.uuid}",
                                 is_resolution=True)
                dpsa.send_result = result or ''
                dpsa.send_status = AlertSendStatus.SUCCEEDED
                dpsa.completed_at = timezone.now()
            except Exception as ex:
                logger.exception(
                    f"Failed to clear alert for delayed start of Task Execution {dpsde.task_execution.uuid}")
                dpsa.send_result = ''
                dpsa.send_status = AlertSendStatus.FAILED
                dpsa.error_message = str(ex)[:Alert.MAX_ERROR_MESSAGE_LENGTH]

            dpsa.save()

@receiver(pre_save, sender=TaskExecution)
def pre_save_task_execution(sender: Type[TaskExecution], **kwargs):
    instance = cast(TaskExecution, kwargs['instance'])

    if instance.pk is None:
        logger.info('Purging Task Execution history before saving new Execution ...')
        num_removed = instance.task.purge_history(reservation_count=1, max_to_purge=50)
        logger.info(f'Purged {num_removed} Task Executions')

    if instance.status != TaskExecution.Status.MANUALLY_STARTED:
        from .delayed_process_start_detection_event import DelayedProcessStartDetectionEvent

        existing_dpsde = DelayedProcessStartDetectionEvent.objects.filter(
            task_execution=instance
        ).order_by('-detected_at', '-id').first()

        if existing_dpsde and (existing_dpsde.resolved_at is None):
            existing_dpsde.resolved_at = timezone.now()
            existing_dpsde.save()
            instance.clear_delayed_task_start_alerts(existing_dpsde)

    current_user = None

    req = get_request()

    if req:
        current_user = req.user

    now = timezone.now()

    if instance.status == TaskExecution.Status.STOPPING:
        if not instance.killed_by:
            instance.killed_by = current_user

        if not instance.kill_started_at:
            instance.kill_started_at = now
    elif instance.status == TaskExecution.Status.STOPPED:
        if not instance.kill_finished_at:
            instance.kill_finished_at = now

    try:
        instance.enrich_settings()
    except Exception as ex:
        logger.warning(f"Failed to enrich Task Execution {instance.uuid} settings",
                exc_info=ex)


@receiver(post_save, sender=TaskExecution)
def post_save_task_execution(sender: TaskExecution, **kwargs):
    from .workflow_task_instance_execution import WorkflowTaskInstanceExecution

    instance = cast(TaskExecution, kwargs['instance'])

    in_progress = instance.is_in_progress()
    task = instance.task

    if in_progress:
        # task may be stale, just update a single column
        task.latest_task_execution = instance
        logger.info(f"post_save_task_execution(): saving {task=} after setting latest execution")
        task.save_without_sync(update_fields=['latest_task_execution', 'updated_at'])

    if task.schedule:
        from .missing_scheduled_task_execution import MissingScheduledTaskExecution
        # TODO: clear multiple?
        # FIXME: does schedule have to match?
        mspe = MissingScheduledTaskExecution.objects.filter(
            task=task, schedule=task.schedule).order_by(
            # use this instead of check below? ) resolved_at__isnull=True
            '-expected_execution_at', '-id').first()

        if mspe and (not mspe.resolved_at):
            from processes.services.schedule_checker import MAX_SCHEDULED_LATENESS_SECONDS
            utc_now = timezone.now()
            lateness_seconds = (utc_now - mspe.expected_execution_at).total_seconds()
            logger.info(f"Found last missing Scheduled Task Execution event {mspe.uuid}, lateness seconds = {lateness_seconds}")

            if lateness_seconds < MAX_SCHEDULED_LATENESS_SECONDS:
                logger.info(
                    f"Task execution {instance.uuid} is {lateness_seconds} seconds after scheduled time of {mspe.expected_execution_at}, clearing alerts")
                mspe.resolved_at = utc_now
                mspe.save()
                instance.clear_missing_scheduled_execution_alerts(mspe)
            else:
                logger.info(
                    f"Task Execution {instance.uuid} is too far ({lateness_seconds} seconds) after scheduled time of {mspe.expected_execution_at}, not clearing alerts")

    heartbeat_interval_seconds = task.heartbeat_interval_seconds
    max_heartbeat_lateness_before_alert_seconds = task.max_heartbeat_lateness_before_alert_seconds

    if heartbeat_interval_seconds and instance.last_heartbeat_at and (max_heartbeat_lateness_before_alert_seconds is not None):
        utc_now = timezone.now()
        last_heartbeat_seconds_ago = (utc_now - instance.last_heartbeat_at).total_seconds()
        if (not in_progress) or (
                last_heartbeat_seconds_ago < heartbeat_interval_seconds + max_heartbeat_lateness_before_alert_seconds):
            from .missing_heartbeat_detection_event import MissingHeartbeatDetectionEvent

            last_heartbeat_detection_event = MissingHeartbeatDetectionEvent.objects.filter(
                task_execution=instance, resolved_at__isnull=True, resolved_event__isnull=True) \
                .order_by('-detected_at').first()

            if last_heartbeat_detection_event:
                logger.info(f"Found last heartbeat detection event {last_heartbeat_detection_event.uuid} to resolve for Task {task.uuid}")
                last_heartbeat_detection_event.resolved_at = utc_now
                last_heartbeat_detection_event.save()

                resolving_event = MissingHeartbeatDetectionEvent(
                    event_at=utc_now,
                    detected_at=utc_now,
                    severity=Event.SEVERITY_INFO,
                    grouping_key=last_heartbeat_detection_event.grouping_key,
                    resolved_event = last_heartbeat_detection_event,
                    task_execution=instance,
                    last_heartbeat_at=instance.last_heartbeat_at,
                    expected_heartbeat_at=last_heartbeat_detection_event.expected_heartbeat_at,
                    heartbeat_interval_seconds=last_heartbeat_detection_event.heartbeat_interval_seconds,
                )
                resolving_event.save()
                instance.send_resolved_missing_heartbeat_detection_notifications(resolving_event)


    wtie = WorkflowTaskInstanceExecution.objects.filter(
        task_execution=instance).first()

    # TODO: use snapshot
    if not in_progress:
        try:
            instance.update_postponed_events()
        except Exception:
            logger.exception(f"Can't update postponed event after error: {instance}")


        if (wtie is None) or wtie.workflow_task_instance.use_task_notification_profiles:
            try:
                instance.maybe_create_and_send_status_change_event()
            except Exception:
                logger.exception(f"Can't send notifications after error: {instance}")

    if wtie:
        workflow_execution = wtie.workflow_execution
        workflow_execution.last_heartbeat_at = max(
            workflow_execution.last_heartbeat_at or workflow_execution.started_at,
            instance.last_heartbeat_at or timezone.now()
        )
        workflow_execution.save()

        if not in_progress:
            if instance.stop_reason in [TaskExecution.StopReason.WORKFLOW_EXECUTION_STOPPED, TaskExecution.StopReason.WORKFLOW_EXECUTION_RETRIED]:
                logger.info('Task Execution was stopped due to workflow stop/retry, not updating workflow')
            elif workflow_execution.is_execution_continuation_allowed():
                logger.info(f"Workflow Execution {workflow_execution.uuid} is allowed to continue")
                logger.info(f"Task {instance.uuid} is a node in Workflow {wtie.workflow_task_instance.workflow.uuid}, handling completion ...")
                wtie.handle_task_execution_finished()
            else:
                logger.info(f"Workflow Execution {workflow_execution.uuid} is not allowed to continue")

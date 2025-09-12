from __future__ import annotations

from typing import Any, Optional, Type, TYPE_CHECKING, cast, override

from datetime import datetime
import logging
from urllib.parse import quote

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Manager
from django.db.models.signals import pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from django.contrib.postgres.fields import HStoreField

from ..common.aws import *
from ..common.utils import coalesce
from ..execution_methods import (
    ExecutionMethod,
    AwsEcsExecutionMethod
)
from ..exception import CommittableException, UnprocessableEntity

from .aws_ecs_configuration import AwsEcsConfiguration
from .run_environment import RunEnvironment
from .schedulable import Schedulable
from .execution import Execution
from .subscription import Subscription
from .task_execution_configuration import TaskExecutionConfiguration


if TYPE_CHECKING:
    from .missing_scheduled_execution_event import MissingScheduledExecutionEvent
    from .missing_scheduled_task_execution_event import MissingScheduledTaskExecutionEvent
    from .task_execution import TaskExecution


logger = logging.getLogger(__name__)


class Task(AwsEcsConfiguration, TaskExecutionConfiguration, Schedulable):
    """
    The specification for a runnable task (job), including details on how to
    run the task and how often the task is supposed to run.
    """

    class Meta:
        db_table = 'processes_processtype'
        unique_together = (('name', 'created_by_group'),)

    # Override Schedulable field so that run_environment is required
    run_environment = models.ForeignKey(RunEnvironment,
        related_name='+', on_delete=models.CASCADE, null=False)

    passive = models.BooleanField(default=False)
    max_manual_start_delay_before_alert_seconds = models.PositiveIntegerField(
        null=True, blank=True, default=600)
    max_manual_start_delay_before_abandonment_seconds = models.PositiveIntegerField(
        null=True, blank=True, default=1200)
    heartbeat_interval_seconds = models.PositiveIntegerField(
        null=True, blank=True, validators=[MinValueValidator(10)])
    max_heartbeat_lateness_before_alert_seconds = models.PositiveIntegerField(
        null=True, blank=True, default=120)
    max_heartbeat_lateness_before_abandonment_seconds = models.PositiveIntegerField(
        null=True, blank=True, default=600)
    service_instance_count = models.PositiveIntegerField(null=True, blank=True)
    min_service_instance_count = models.PositiveIntegerField(
        null=True, blank=True)

    project_url = models.CharField(max_length=1000, blank=True)
    log_query = models.CharField(max_length=1000, blank=True)

    execution_method_type = models.CharField(max_length=100, null=False,
            blank=False, default='Unknown')

    execution_method_capability_details = models.JSONField(null=True, blank=True)

    scheduling_provider_type = models.CharField(max_length=100, blank=True)
    scheduling_settings = models.JSONField(null=True, blank=True)

    service_provider_type = models.CharField(max_length=100, blank=True)
    service_settings = models.JSONField(null=True, blank=True)

    input_value_schema = models.JSONField(null=True, blank=True)
    default_input_value = models.JSONField(null=True, blank=True)
    output_value_schema = models.JSONField(null=True, blank=True)

    # Start Deprecated
    aws_ecs_task_definition_arn = models.CharField(max_length=1000, blank=True)
    aws_ecs_service_load_balancer_health_check_grace_period_seconds = \
            models.IntegerField(null=True, blank=True)
    aws_ecs_service_deploy_rollback_on_failure = \
            models.BooleanField(null=True, blank=True)
    aws_ecs_service_deploy_minimum_healthy_percent = \
            models.IntegerField(null=True, blank=True)
    aws_ecs_service_deploy_maximum_percent = \
            models.IntegerField(null=True, blank=True)
    aws_ecs_service_deploy_enable_circuit_breaker = \
            models.BooleanField(null=True, blank=True)
    aws_ecs_service_enable_ecs_managed_tags = \
            models.BooleanField(null=True, blank=True)
    aws_ecs_service_propagate_tags = \
            models.CharField(max_length=20,
            blank=True, choices=[(x, x) for x in AwsEcsExecutionMethod.SERVICE_PROPAGATE_TAGS_CHOICES])
    aws_ecs_service_tags = HStoreField(blank=True, null=True)

    aws_ecs_service_force_new_deployment = \
            models.BooleanField(null=True, blank=True)

    aws_ecs_main_container_name = models.CharField(max_length=1000, blank=True)
    aws_scheduled_execution_rule_name = models.CharField(max_length=1000,
            blank=True)
    aws_scheduled_event_rule_arn = models.CharField(max_length=1000, blank=True)
    aws_event_target_rule_name = models.CharField(max_length=1000, blank=True)
    aws_event_target_id = models.CharField(max_length=1000, blank=True)
    aws_ecs_service_arn = models.CharField(max_length=1000, blank=True)
    # End deprecated

    aws_ecs_service_updated_at = models.DateTimeField(null=True, blank=True)

    is_scheduling_managed = models.BooleanField(default=None, null=True)
    scheduling_provider_type = models.CharField(max_length=100, blank=True)
    scheduling_settings = models.JSONField(null=True, blank=True)

    is_service_managed = models.BooleanField(default=None, null=True)
    service_provider_type = models.CharField(max_length=100, blank=True)
    service_settings = models.JSONField(null=True, blank=True)

    # Deprecated
    alert_methods = models.ManyToManyField('AlertMethod', blank=True)

    latest_task_execution = models.OneToOneField('TaskExecution',
        # Don't backreference, since TaskExecutions already point to Tasks
        related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True,
        db_column='latest_process_execution_id')

    was_auto_created = models.BooleanField(default=False, null=True)

    should_skip_synchronize_with_run_environment = False

    def get_aws_region(self) -> Optional[str]:
        if self.run_environment is None:
            return None

        return self.run_environment.get_aws_region()

    @override
    @property
    def kind_label(self) -> str:
        return 'Task'

    @override
    @property
    def dashboard_path(self) -> str:
        return 'tasks'

    @override
    def executions(self) -> Manager[TaskExecution]:
        from .task_execution import TaskExecution
        return TaskExecution.objects.filter(task=self)

    @override
    def lookup_missing_scheduled_execution_events(self) -> Manager[MissingScheduledTaskExecutionEvent]:
        from .missing_scheduled_task_execution_event import MissingScheduledTaskExecutionEvent

        return MissingScheduledTaskExecutionEvent.objects.filter(task=self,
                resolved_at__isnull=True, resolved_event__isnull=True)

    @override
    def make_resolved_missing_scheduled_execution_event(self, detected_at: datetime,
        resolved_event: MissingScheduledExecutionEvent, execution: Execution) -> MissingScheduledTaskExecutionEvent:
        from .task_execution import TaskExecution
        from .missing_scheduled_task_execution_event import MissingScheduledTaskExecutionEvent

        resolving_event = MissingScheduledTaskExecutionEvent(
            event_at=execution.started_at, detected_at=detected_at,
            severity=resolved_event.severity, resolved_event=resolved_event,
            created_by_group=self.created_by_group, task=self,
            task_execution=cast(TaskExecution, execution),
            expected_execution_at=resolved_event.expected_execution_at,
            schedule=self.schedule,
        )
        resolving_event.save()
        return resolving_event

    @property
    def is_service(self) -> bool:
        return self.service_instance_count is not None

    def in_progress_executions_queryset(self):
        from .task_execution import TaskExecution
        return self.taskexecution_set.filter(status__in=TaskExecution.IN_PROGRESS_STATUSES)

    def running_executions_queryset(self):
        from .task_execution import TaskExecution
        return self.taskexecution_set.filter(status=TaskExecution.Status.RUNNING)

    @override
    def concurrency_at(self, dt: datetime) -> int:
        from .task_execution import TaskExecution

        # TODO: add index for this
        return TaskExecution.objects.filter(
            models.Q(task=self) & (
                models.Q(started_at__lte=dt) |
                models.Q(started_at__isnull=True)
            ) & (
                models.Q(finished_at__gte=dt) |
                models.Q(finished_at__isnull=True)
            ) & (
                models.Q(marked_done_at__gte=dt) |
                models.Q(marked_done_at__isnull=True)
            )
        ).count()

    @override
    def can_start_execution(self) -> bool:
        if self.max_concurrency and (self.max_concurrency > 0):
            existing_concurrency = self.running_executions_queryset().count()

            logger.info(f"Running executions = {existing_concurrency} out of {self.max_concurrency}")

            if existing_concurrency >= self.max_concurrency:
                return False

        return True

    @property
    def logs_url(self) -> Optional[str]:
        lq = self.log_query
        if lq:
            if lq.startswith('http://') or lq.startswith('https://'):
                return lq
            else:
                # Assume Cloudwatch logs
                run_env = self.run_environment
                region = 'us-west-2'
                if run_env:
                    region = run_env.aws_default_region or region

                limit = 2000

                return f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#logs-insights:queryDetail=~(end~0~start~-86400~timeType~'RELATIVE~unit~'seconds~editorString~'fields*20*40timestamp*2c*20*40message*0a*7c*20sort*20*40timestamp*20desc*0a*7c*20limit*20{limit}~isLiveTail~false~source~(~'" + \
                        quote(lq, safe='').replace('%', '*') + '))'
        else:
            return None


    def purge_history(self, reservation_count: int = 0,
            max_to_purge: int = -1) -> int:
        from .task_execution import TaskExecution

        logger.info(f'Starting purge_history() for Task {self.uuid} ...')

        usage_limits = Subscription.compute_usage_limits(self.created_by_group)

        max_items = usage_limits.max_task_execution_history_items

        if max_items is None:
            logger.info("purge_history: no limit on Task Execution history count")
            return 0

        remaining_items = max_items - reservation_count

        qs = self.taskexecution_set

        execution_count = qs.count()
        items_to_remove = execution_count - remaining_items

        if max_to_purge > 0:
            items_to_remove = min(items_to_remove, max_to_purge)

        if items_to_remove <= 0:
            logger.info(f"purge_history: {execution_count=} < {remaining_items=}, no need to purge")
            return 0

        logger.info(f'Removing {items_to_remove=} Task Execution history items for Task {self.uuid} ...')

        completed_qs = qs.exclude(
                status__in=TaskExecution.IN_PROGRESS_STATUSES) \
                .order_by('finished_at')[0:items_to_remove]

        num_completed_deleted = 0
        for te in completed_qs.iterator():
            if num_completed_deleted >= items_to_remove:
                break

            try:
                te.delete()
                num_completed_deleted += 1
            except Exception:
                logger.warning(f"Failed to delete completed Task Execution {te.uuid}",
                        exc_info=True)

        logger.info(f'Removed {num_completed_deleted=} completed Task Execution history items for Task {self.uuid}')

        items_to_remove -= num_completed_deleted

        if items_to_remove <= 0:
            logger.info(f'No need to remove any in-progress Task Execution history items for Task {self.uuid}')
            return num_completed_deleted

        logger.warning(f"Must remove {items_to_remove=} Task Executions for Task {self.uuid} that are still in-progress")

        in_progress_qs = self.in_progress_executions_queryset() \
                .order_by('started_at')[0:items_to_remove]

        num_in_progress_deleted = 0
        for te in in_progress_qs.iterator():
            if num_in_progress_deleted >= items_to_remove:
                break

            logger.info(f'Deleting in-progress {te=} with {te.started_at=} for Task {self.uuid}')

            try:
                te.delete()
                num_in_progress_deleted += 1
            except Exception:
                logger.warning(f'Failed to delete in-progress Task Execution {te.uuid} for Task {self.uuid}',
                        exc_info=True)

        logger.info(f'Removed {num_in_progress_deleted=} in-progress Task Execution history items for Task {self.uuid}')
        return num_completed_deleted + num_in_progress_deleted

    def execution_method(self) -> ExecutionMethod:
        return ExecutionMethod.make_execution_method(task=self)

    def save_without_sync(self, **kwargs) -> 'Task':
        old_sync = self.should_skip_synchronize_with_run_environment
        self.should_skip_synchronize_with_run_environment = True
        try:
            self.save(**kwargs)
            return self
        finally:
            self.should_skip_synchronize_with_run_environment = old_sync

    def has_active_managed_scheduled_execution(self, current: bool=True) -> bool:
        # TODO: just check is_scheduling_managed once it is migrated
        return self.enabled and (not self.passive) and bool(self.schedule) and \
                coalesce(self.is_scheduling_managed, not current)

    def is_active_managed_service(self, current: bool=True) -> bool:
         # TODO: just check is_service_managed once it is migrated
        return self.enabled and (not self.passive) and self.is_service and \
                coalesce(self.is_service_managed, not current)

    def synchronize_with_run_environment(self, old_self: Optional['Task']=None,
            is_saving: bool=False) -> bool:
        if self.passive and ((not old_self) or old_self.passive):
            return False

        execution_method = self.execution_method()

        old_execution_method: Optional[ExecutionMethod] = None

        if old_self:
            old_execution_method = old_self.execution_method()

        if old_self and (self.schedule != old_self.schedule):
            self.schedule_updated_at = timezone.now()

        should_update_scheduled_execution, should_force_create_scheduled_execution = \
                execution_method.should_update_or_force_recreate_scheduled_execution(
                        old_execution_method=old_execution_method)

        logger.info(f"synchronize_with_run_environment(): {self.uuid=} Updating scheduled execution, {self.schedule=}, {should_update_scheduled_execution=}, {should_force_create_scheduled_execution=} ...")

        if should_update_scheduled_execution:
            logger.info(f"synchronize_with_run_environment(): Updating scheduled_execution, {self.is_scheduling_managed=}, {self.enabled=} ...")

            schedule_teardown_completed_at: Optional[datetime] = None
            schedule_teardown_result: Optional[Any] = None
            torndown_scheduling_settings: Optional[dict[str, Any]] = None

            will_be_managed_scheduled_execution = \
                    self.has_active_managed_scheduled_execution(current=False)

            if will_be_managed_scheduled_execution and \
                    (not execution_method.supports_capability(
                        ExecutionMethod.ExecutionCapability.SCHEDULING)):
                raise APIException(f"Execution method {execution_method.name} does not support scheduled executions")

            if (should_force_create_scheduled_execution or (not will_be_managed_scheduled_execution)) and \
                    old_execution_method and old_self and \
                    old_self.has_active_managed_scheduled_execution():
                # TODO: option to ignore error tearing down
                torndown_scheduling_settings, schedule_teardown_result = \
                        old_execution_method.teardown_scheduled_execution()
                schedule_teardown_completed_at = timezone.now()

            if will_be_managed_scheduled_execution:
                try:
                    execution_method.setup_scheduled_execution(
                            old_execution_method=old_execution_method,
                            force_creation=should_force_create_scheduled_execution,
                            teardown_result=schedule_teardown_result)
                except Exception as ex:
                    logger.exception("Failed to setup scheduled_execution for Task {self.uuid}")

                    # FIXME: due to AtomicUpdateModelMixin all changes will
                    # probably be rolled back.
                    if schedule_teardown_completed_at:
                        self.scheduling_settings = torndown_scheduling_settings
                        if self.pk:
                            self.save_without_sync()
                    raise ex

                self.is_scheduling_managed = True
            else:
                if old_execution_method:
                    # FIXME: this overwrites settings
                    self.scheduling_settings, _teardown_result = \
                            old_execution_method.teardown_scheduled_execution()

                if self.is_scheduling_managed is not False:
                    self.is_scheduling_managed = None
        else:
            logger.debug("Not updating scheduling params")


        should_update_service, should_force_create_service = \
            execution_method.should_update_or_force_recreate_service(
                    old_execution_method=old_execution_method)

        logger.info(f"synchronize_with_run_environment(): {self.uuid=} Updating service, {self.is_service=}, {should_update_service=}, {should_force_create_service=} ...")

        if should_update_service:
            logger.info(f"synchronize_with_run_environment(): {self.uuid=} Updating service, {self.is_service=}, {self.enabled=}, {self.is_service_managed=} ...")

            service_teardown_completed_at: Optional[datetime] = None
            service_teardown_result: Optional[Any] = None
            torndown_service_settings: Optional[dict[str, Any]] = None

            will_be_managed_service = self.is_active_managed_service(current=False)

            if will_be_managed_service and \
                    (not execution_method.supports_capability(
                        ExecutionMethod.ExecutionCapability.SETUP_SERVICE)):
                raise APIException(f"Execution method {execution_method.name} does not support service setup")

            if (should_force_create_service or (not will_be_managed_service)) and \
                    old_execution_method and old_self and \
                    old_self.is_active_managed_service():
                # TODO: option to ignore error tearing down

                logger.info(f"synchronize_with_run_environment(): {self.uuid=} tearing service down before setup")
                torndown_service_settings, service_teardown_result = old_execution_method.teardown_service()
                service_teardown_completed_at = timezone.now()

            logger.info(f"synchronize_with_run_environment(): {self.uuid=} {will_be_managed_service=}, {torndown_service_settings=}, {service_teardown_result=}")

            if will_be_managed_service:
                try:
                    execution_method.setup_service(
                            old_execution_method=old_execution_method,
                            force_creation=should_force_create_service,
                            teardown_result=service_teardown_result)
                except Exception as ex:
                    msg = f"Failed to setup service for Task {self.uuid}"
                    logger.exception(msg)

                    if service_teardown_completed_at:
                        logger.info(f"Saving torndown service settings locally {self.uuid=} ...")
                        self.service_settings = torndown_service_settings
                        self.aws_ecs_service_updated_at = service_teardown_completed_at
                        if self.pk:
                            logger.info(f"Saving torndown service settings in DB {self.uuid=} ...")
                            self.save_without_sync()
                            logger.info(f"Done saving torndown service settings in DB {self.uuid=}")

                    raise CommittableException(cause=ex)

                self.is_service_managed = True
            else:
                if old_execution_method:
                    logger.info(f"synchronize_with_run_environment(): {self.uuid=} tearing down service because Task will no longer be managed ...")

                    self.service_settings, _teardown_result = \
                            old_execution_method.teardown_service()

                if self.is_service_managed:
                    self.is_service_managed = None
        else:
            logger.info(f"Not updating service params {self.uuid=}")

        if is_saving:
            self.save_without_sync()

        return should_update_scheduled_execution or should_update_service

    def enrich_settings(self) -> None:
        self.execution_method().enrich_task_settings()


@receiver(pre_save, sender=Task)
def pre_save_task(sender: Type[Task], **kwargs):
    instance = kwargs['instance']
    logger.info(f"pre_save_task with Task {instance}")

    if instance.pk is None:
        usage_limits = Subscription.compute_usage_limits(instance.created_by_group)
        max_tasks = usage_limits.max_tasks

        existing_count = Task.objects.filter(
                created_by_group=instance.created_by_group).count()

        if (max_tasks is not None) and (existing_count >= max_tasks):
            raise UnprocessableEntity(detail='Task limit exceeded', code='limit_exceeded')

    if instance.should_skip_synchronize_with_run_environment:
        logger.info(f"skipping synchronize_with_run_environment with Task {instance}")
    else:
        old_self: Optional[Task] = None

        if instance.id:
            old_self = Task.objects.filter(id=instance.id).first()

        instance.synchronize_with_run_environment(old_self=old_self,
                is_saving=False)

    try:
        instance.enrich_settings()
    except Exception as ex:
        logger.warning(f"Failed to enrich Task {instance.uuid} settings", exc_info=ex)

@receiver(pre_delete, sender=Task)
def pre_delete_task(sender: Type[Task], **kwargs) -> None:
    task = cast(Task, kwargs['instance'])
    logger.info(f"pre-save with instance {task}")

    if task.enabled and (not task.passive):
        execution_method = task.execution_method()
        if task.has_active_managed_scheduled_execution():
            execution_method.teardown_scheduled_execution()

        if task.is_active_managed_service():
            execution_method.teardown_service()

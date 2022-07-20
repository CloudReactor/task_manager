from typing import Optional, Type, cast

from datetime import datetime
import logging
import re
from urllib.parse import quote

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from django.contrib.postgres.fields import HStoreField

from ..common.aws import *
from ..execution_methods import (
    ExecutionMethod,
    AwsEcsExecutionMethod,
    UnknownExecutionMethod
)
from ..exception.unprocessable_entity import UnprocessableEntity

from .subscription import Subscription
from .aws_ecs_configuration import AwsEcsConfiguration
from .schedulable import Schedulable
from .infrastructure_configuration import InfrastructureConfiguration
from .run_environment import RunEnvironment

logger = logging.getLogger(__name__)


class Task(AwsEcsConfiguration, InfrastructureConfiguration, Schedulable):
    """
    The specification for a runnable task (job), including details on how to
    run the task and how often the task is supposed to run.
    """

    AWS_ECS_SCHEDULE_ATTRIBUTES = [
        'schedule',
        'aws_default_subnets',
        'aws_ecs_task_definition_arn',
        'aws_ecs_default_launch_type',
        'aws_ecs_default_cluster_arn',
        'aws_ecs_default_security_groups',
        'aws_ecs_default_execution_role',
        'aws_ecs_default_task_role',
        'enabled'
    ]

    # attr => must_recreate
    AWS_ECS_SERVICE_ATTRIBUTES = {
        'service_instance_count': False,
        'aws_default_subnets': False,
        'aws_ecs_task_definition_arn': False,
        'aws_ecs_default_launch_type': True,
        'aws_ecs_default_cluster_arn': True,
        'aws_ecs_default_security_groups': False,
        'aws_ecs_service_load_balancer_health_check_grace_period_seconds': False,
        'aws_ecs_service_deploy_enable_circuit_breaker': False,
        'aws_ecs_service_deploy_rollback_on_failure': False,
        'aws_ecs_service_deploy_minimum_healthy_percent': False,
        'aws_ecs_service_deploy_maximum_percent': False,
        'aws_ecs_service_enable_ecs_managed_tags': False,
        'aws_ecs_service_propagate_tags': False,
        'aws_ecs_service_tags': False,
        'enabled': True
    }

    DEFAULT_ECS_SERVICE_LOAD_BALANCER_HEALTH_CHECK_GRACE_PERIOD_SECONDS = 300

    SERVICE_NAME_REGEX = re.compile(r"^(.+?)(_(\d+))?$")

    class Meta:
        db_table = 'processes_processtype'
        unique_together = (('name', 'created_by_group'),)

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

    # TODO: use when running - might need to pass to process wrapper for
    # scheduled processes
    environment_variables_overrides = models.JSONField(null=True, blank=True)

    project_url = models.CharField(max_length=1000, blank=True)
    log_query = models.CharField(max_length=1000, blank=True)
    run_environment = models.ForeignKey(RunEnvironment,
            on_delete=models.CASCADE, blank=True)

    execution_method_type = models.CharField(max_length=100, null=False,
            blank=False, default='Unknown')

    execution_method_capability_details = models.JSONField(null=True, blank=True)

    scheduling_provider_type = models.CharField(max_length=100, blank=True)
    scheduling_settings = models.JSONField(null=True, blank=True)

    service_provider_type = models.CharField(max_length=100, blank=True)
    service_settings = models.JSONField(null=True, blank=True)

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
    aws_ecs_service_updated_at = models.DateTimeField(null=True, blank=True)

    infrastructure_type = models.CharField(max_length=100, blank=True)
    infrastructure_settings = models.JSONField(null=True, blank=True)

    scheduling_provider_type = models.CharField(max_length=100, blank=True)
    scheduling_settings = models.JSONField(null=True, blank=True)

    service_provider_type = models.CharField(max_length=100, blank=True)
    service_settings = models.JSONField(null=True, blank=True)

    allocated_cpu_units = models.PositiveIntegerField(null=True, blank=True)
    allocated_memory_mb = models.PositiveIntegerField(null=True, blank=True)
    alert_methods = models.ManyToManyField('AlertMethod', blank=True)
    other_metadata = models.JSONField(null=True, blank=True)
    latest_task_execution = models.OneToOneField('TaskExecution',
        # Don't backreference, since TaskExecutions already point to Tasks
        related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True,
        db_column='latest_process_execution_id')

    was_auto_created = models.BooleanField(default=False, null=True)

    should_skip_synchronize_with_run_environment = False
    aws_ecs_should_force_service_creation = False

    def get_aws_region(self) -> str:
        return self.run_environment.get_aws_region()

    @property
    def dashboard_path(self) -> str:
        return 'tasks'

    @property
    def infrastructure_website_url(self) -> Optional[str]:
        return make_aws_console_ecs_task_definition_url(
                self.aws_ecs_task_definition_arn)

    @property
    def aws_ecs_task_definition_infrastructure_website_url(self) -> Optional[str]:
        return make_aws_console_ecs_task_definition_url(
                self.aws_ecs_task_definition_arn)

    @property
    def is_service(self) -> bool:
        return self.service_instance_count is not None

    @property
    def aws_ecs_service_infrastructure_website_url(self) -> Optional[str]:
        return make_aws_console_ecs_service_url(
                ecs_service_arn=self.aws_ecs_service_arn,
                cluster_name=extract_cluster_name(self.aws_ecs_default_cluster_arn))

    def in_progress_executions_queryset(self):
        from .task_execution import TaskExecution
        return self.taskexecution_set.filter(status__in=TaskExecution.IN_PROGRESS_STATUSES)

    def running_executions_queryset(self):
        from .task_execution import TaskExecution
        return self.taskexecution_set.filter(status=TaskExecution.Status.RUNNING)

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
                region = run_env.aws_default_region or 'us-west-2'
                limit = 2000

                # FIXME: does not handle queries with capital letters
                return f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#logs-insights:queryDetail=~(end~0~start~-86400~timeType~'RELATIVE~unit~'seconds~editorString~'fields*20*40timestamp*2c*20*40message*0a*7c*20sort*20*40timestamp*20desc*0a*7c*20limit*20{limit}~isLiveTail~false~source~(~'" + \
                        quote(lq, safe='').replace('%', '*').lower() + '))'
        else:
            return None

    def purge_history(self, reservation_count: int = 0,
            max_to_purge: int = -1) -> int:
        from .task_execution import TaskExecution

        logger.info(f'Starting purge_history() for Task {self.uuid} ...')

        usage_limits = Subscription.compute_usage_limits(self.created_by_group)
        max_items = usage_limits.max_task_execution_history_items - reservation_count

        qs = self.taskexecution_set

        execution_count = qs.count()
        items_to_remove = execution_count - max_items

        if max_to_purge > 0:
            items_to_remove = min(items_to_remove, max_to_purge)

        if items_to_remove <= 0:
            logger.info(f"purge_history: {execution_count=} < {max_items=}, no need to purge")
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

    def execution_method(self):
        from processes.execution_methods import (
            AwsEcsExecutionMethod, AwsLambdaExecutionMethod
        )

        if self.execution_method_type == AwsEcsExecutionMethod.NAME:
            return AwsEcsExecutionMethod(task=self)
        elif self.execution_method_type == AwsLambdaExecutionMethod.NAME:
            return AwsLambdaExecutionMethod(task=self)
        return UnknownExecutionMethod(task=self)

    # def setup_scheduled_execution(self) -> None:
    #     logger.info(f"Task.setup_scheduled_execution() for task #{self.uuid}")
    #     self.execution_method().setup_scheduled_execution()

    # def teardown_scheduled_execution(self) -> None:
    #     logger.info(f"Task.teardown_scheduled_execution() for task #{self.uuid}")
    #     self.execution_method().teardown_scheduled_execution()

    # def setup_service(self, force_creation=False):
    #     logger.info(f"Task.setup_service() for task #{self.uuid}")
    #     return self.execution_method().setup_service(force_creation=force_creation)

    # def teardown_service(self) -> None:
    #     logger.info(f'Task.teardown_service() for task #{self.uuid}')
    #     self.execution_method().teardown_service()

    def synchronize_with_run_environment(self, old_self=None, is_saving=False) -> bool:
        if self.passive:
            return False

        should_update_schedule = False
        should_force_create_service = self.aws_ecs_should_force_service_creation

        if old_self:
            if self.schedule != old_self.schedule:
                self.schedule_updated_at = timezone.now()

            for attr in Task.AWS_ECS_SCHEDULE_ATTRIBUTES:
                new_value = getattr(self, attr)
                old_value = getattr(old_self, attr)

                if new_value != old_value:
                    logger.info(f"{attr} changed from {old_value} to {new_value}, adjusting schedule")
                    should_update_schedule = True

            should_update_service = self.aws_ecs_should_force_service_creation
            for attr, must_recreate in Task.AWS_ECS_SERVICE_ATTRIBUTES.items():
                new_value = getattr(self, attr)
                old_value = getattr(old_self, attr)

                if new_value != old_value:
                    logger.info(f"{attr} changed from {old_value} to {new_value}, adjusting service")
                    should_update_service = True
                    should_force_create_service = should_force_create_service or must_recreate
        else:
            should_update_schedule = True
            should_update_service = True
            should_force_create_service = True

        execution_method = self.execution_method()
        should_update_schedule = should_update_schedule and \
                execution_method.supports_capability(
                        ExecutionMethod.ExecutionCapability.SCHEDULING)
        should_update_service = should_update_service and \
                execution_method.supports_capability(
                        ExecutionMethod.ExecutionCapability.SETUP_SERVICE)

        if should_update_schedule:
            logger.info("pre_save_task(): Updating schedule params ...")
            if self.schedule and self.enabled:
                execution_method.setup_scheduled_execution()
            else:
                execution_method.teardown_scheduled_execution()
            logger.info("Done updating schedule params ...")
        else:
            logger.debug("Not updating schedule params")

        if should_update_service:
            logger.info("synchronize_with_run_environment(): Updating service...")
            if self.is_service and self.enabled:
                execution_method.setup_service(force_creation=should_force_create_service)
            else:
                execution_method.teardown_service()
        else:
            logger.debug("Not updating service params")

        if not is_saving:
            self.should_skip_synchronize_with_run_environment = True
            try:
                self.save()
            finally:
                self.should_skip_synchronize_with_run_environment = False

        self.aws_ecs_should_force_service_creation = False

        return should_update_schedule or should_update_service

    def enrich_settings(self) -> None:
        self.execution_method().enrich_task_settings()


@receiver(pre_save, sender=Task)
def pre_save_task(sender: Type[Task], **kwargs):
    instance = kwargs['instance']
    logger.info(f"pre-save with task {instance}")

    if instance.pk is None:
        old_self = None
        usage_limits = Subscription.compute_usage_limits(instance.created_by_group)
        max_tasks = usage_limits.max_tasks

        existing_count = Task.objects.filter(
                created_by_group=instance.created_by_group).count()

        if existing_count >= max_tasks:
            raise UnprocessableEntity(detail='Task limit exceeded', code='limit_exceeded')
    else:
        old_self = Task.objects.filter(id=instance.id).first()

    from .convert_legacy_em_and_infra import populate_task_emc_and_infra

    if instance.execution_method_type == AwsEcsExecutionMethod.NAME:
        populate_task_emc_and_infra(instance)

    if instance.should_skip_synchronize_with_run_environment:
        logger.info(f"skipping synchronize_with_run_environment with Task {instance}")
    else:
        changed = instance.synchronize_with_run_environment(old_self=old_self,
                is_saving=True)

        if changed:
            populate_task_emc_and_infra(instance)

    instance.enrich_settings()


@receiver(pre_delete, sender=Task)
def pre_delete_task(sender: Type[Task], **kwargs) -> None:
    task = cast(Task, kwargs['instance'])
    logger.info(f"pre-save with instance {task}")

    execution_method = task.execution_method()

    if task.schedule:
        execution_method.teardown_scheduled_execution()

    if task.is_service:
        execution_method.teardown_service()

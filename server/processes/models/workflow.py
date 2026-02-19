from __future__ import annotations

from typing import Optional, Type, TYPE_CHECKING, cast, override

from datetime import datetime
import json
import logging
import uuid as python_uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Manager
from django.db.models.signals import pre_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from django_middleware_global_request.middleware import get_request

from rest_framework import serializers
from rest_framework.exceptions import APIException

from botocore.exceptions import ClientError

from ..common.utils import generate_clone_name
from ..common.aws import handle_aws_multiple_failure_response
from ..exception import UnprocessableEntity
from ..execution_methods.aws_settings import AwsSettings, INFRASTRUCTURE_TYPE_AWS

from .user_group_access_level import UserGroupAccessLevel
from .subscription import Subscription
from .saas_token import SaasToken
from .schedulable import Schedulable
from .execution import Execution
from .run_environment import RunEnvironment
from .workflow_transition import WorkflowTransition


if TYPE_CHECKING:
    from .missing_scheduled_execution_event import MissingScheduledExecutionEvent
    from .missing_scheduled_workflow_execution_event import MissingScheduledWorkflowExecutionEvent
    from .workflow_execution import WorkflowExecution


logger = logging.getLogger(__name__)


class Workflow(Schedulable):
    AWS_SCHEDULE_ATTRIBUTES = [
        'schedule',
        'enabled'
    ]

    class Meta:
        ordering = ['name']
        unique_together = (('name', 'created_by_group'),)

    latest_workflow_execution = models.OneToOneField('WorkflowExecution',
        # Don't backreference, since WorkflowExecutions already point to Workflows
        related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True)

    scheduling_run_environment = models.ForeignKey(RunEnvironment, on_delete=models.SET_NULL, blank=True, null=True)
    aws_scheduled_execution_rule_name = models.CharField(max_length=1000, blank=True)
    aws_scheduled_event_rule_arn = models.CharField(max_length=1000, blank=True)
    aws_event_target_rule_name = models.CharField(max_length=1000, blank=True)
    aws_event_target_id = models.CharField(max_length=1000, blank=True)

    # Legacy
    alert_methods = models.ManyToManyField('AlertMethod', blank=True)

    def workflow_transitions(self):
        return WorkflowTransition.objects.filter(to_workflow_task_instance__workflow=self)

    def in_progress_executions_queryset(self):
        from .workflow_execution import WorkflowExecution
        return self.workflowexecution_set.filter(
                status__in=WorkflowExecution.IN_PROGRESS_STATUSES)

    def running_executions_queryset(self):
        from .workflow_execution import WorkflowExecution
        return self.workflowexecution_set.filter(
            status=Execution.Status.RUNNING
        )

    @override
    @property
    def kind_label(self) -> str:
        return 'Workflow'

    @override
    def concurrency_at(self, dt: datetime) -> int:
        from .workflow_execution import WorkflowExecution
        # TODO: add index for this
        return WorkflowExecution.objects.filter(
            models.Q(workflow=self) &
            models.Q(started_at__lte=dt) & (
                models.Q(finished_at__gte=dt) |
                models.Q(finished_at__isnull=True)
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

    @override
    def executions(self) -> Manager[WorkflowExecution]:
        from .workflow_execution import WorkflowExecution
        return WorkflowExecution.objects.filter(workflow=self)

    @override
    def lookup_all_missing_scheduled_execution_events(self) -> Manager[MissingScheduledWorkflowExecutionEvent]:
        from .missing_scheduled_workflow_execution_event import MissingScheduledWorkflowExecutionEvent
        return MissingScheduledWorkflowExecutionEvent.objects.filter(workflow=self)

    @override
    def make_resolved_missing_scheduled_execution_event(self, detected_at: datetime,
        resolved_event: MissingScheduledExecutionEvent, execution: Execution) -> MissingScheduledWorkflowExecutionEvent:
        from .workflow_execution import WorkflowExecution
        from .missing_scheduled_workflow_execution_event import MissingScheduledWorkflowExecutionEvent

        resolving_event = MissingScheduledWorkflowExecutionEvent(
            event_at=execution.started_at, detected_at=detected_at,
            severity=resolved_event.severity,
            resolved_event=resolved_event,
            created_by_group=self.created_by_group,
            workflow=self, workflow_execution=cast(WorkflowExecution, execution),
            expected_execution_at=resolved_event.expected_execution_at,
            schedule=self.schedule,
        )
        resolving_event.save()
        return resolving_event

    def find_start_task_instances(self):
        non_root_task_instance_ids = list(
            self.workflow_transitions().values_list(
                'to_workflow_task_instance__id', flat=True).distinct())

        return self.workflow_task_instances.exclude(id__in=non_root_task_instance_ids)

    def clone(self, data):
        workflow = self
        original_id = self.id

        # Deprecated
        original_alert_methods = self.alert_methods.all()

        original_notification_profiles = self.notification_profiles.all()

        workflow.pk = None
        workflow.uuid = python_uuid.uuid4()
        workflow.name = data.get('name', generate_clone_name(workflow.name))
        workflow.created_at = timezone.now()
        workflow.updated_at = timezone.now()
        workflow.latest_workflow_execution = None
        workflow.aws_scheduled_execution_rule_name = ''
        workflow.aws_scheduled_event_rule_arn = ''
        workflow.aws_event_target_rule_name = ''
        workflow.aws_event_target_id = ''
        workflow.schedule = ''
        workflow.schedule_updated_at = timezone.now()
        workflow.save()

        # Deprecated
        workflow.alert_methods.set(original_alert_methods)
        workflow.save()

        workflow.notification_profiles.set(original_notification_profiles)
        workflow.save()

        original_workflow = Workflow.objects.get(id=original_id)

        original_to_cloned_wti_id = {}

        for wti in original_workflow.workflow_task_instances.all():
            original_wti_id = wti.id
            wti.pk = None
            wti.uuid = python_uuid.uuid4()
            wti.workflow = workflow
            wti.created_at = timezone.now()
            wti.updated_at = timezone.now()
            wti.save()
            original_to_cloned_wti_id[original_wti_id] = wti.id

        for wt in original_workflow.workflow_transitions():
            from_wti_id = wt.from_workflow_task_instance.id
            to_wti_id = wt.to_workflow_task_instance.id

            wt.pk = None
            wt.uuid = python_uuid.uuid4()
            wt.from_workflow_task_instance_id = original_to_cloned_wti_id[from_wti_id]
            wt.to_workflow_task_instance_id = original_to_cloned_wti_id[to_wti_id]
            wt.created_at = timezone.now()
            wt.updated_at = timezone.now()
            wt.save()

        return workflow

    def purge_history(self, reservation_count: int = 0,
            max_to_purge: int = -1) -> int:
        from .workflow_execution import WorkflowExecution

        logger.info(f'Starting purge_history() for Workflow {self.uuid} ...')

        usage_limits = Subscription.compute_usage_limits(self.created_by_group)

        max_items = usage_limits.max_workflow_execution_history_items

        if max_items is None:
            logger.info("purge_history: no limit on Workflow Execution history count")
            return 0

        remaining_items = max_items - reservation_count

        qs = self.workflowexecution_set

        execution_count = qs.count()
        items_to_remove = execution_count - remaining_items

        if max_to_purge > 0:
            items_to_remove = min(items_to_remove, max_to_purge)

        if items_to_remove <= 0:
            logger.info(f"purge_history: {execution_count=} < {remaining_items=}, no need to purge")
            return 0

        logger.info(f"Removing {items_to_remove=} Workflow Execution history items ...")

        completed_qs = qs.exclude(
                status__in=WorkflowExecution.IN_PROGRESS_STATUSES) \
                .order_by('finished_at')[0:items_to_remove]

        num_completed_deleted = 0
        for we in completed_qs.iterator():
            if num_completed_deleted >= items_to_remove:
                break

            try:
                we.delete()
                num_completed_deleted += 1
            except Exception:
                logger.warning(f"Failed to delete completed Workflow Execution {we.uuid}",
                        exc_info=True)

        logger.info(f"Removed {num_completed_deleted=} completed Workflow Execution history items")

        items_to_remove -= num_completed_deleted

        if items_to_remove <= 0:
            logger.info('No need to remove any in-progress Workflow Execution history items')
            return num_completed_deleted

        logger.warning(f"Must remove {items_to_remove=} Workflow Executions that are still in-progress")

        in_progress_qs = self.in_progress_executions_queryset() \
                .order_by('started_at')[0:items_to_remove]

        num_in_progress_deleted = 0
        for we in in_progress_qs.iterator():
            if num_in_progress_deleted >= items_to_remove:
                break

            logger.info(f"Deleting in-progress {we=} with {we.started_at=}")

            try:
                we.delete()
                num_in_progress_deleted += 1
            except Exception:
                logger.warning(f"Failed to delete in-progress Workflow Execution {we.uuid}",
                        exc_info=True)

        logger.info(f"Removed {num_in_progress_deleted=} in-progress Workflow Execution history items")
        return num_completed_deleted + num_in_progress_deleted

    @override
    def setup_scheduled_execution(self, run_environment: RunEnvironment) -> None:
        from .workflow_execution import WorkflowExecution

        logger.info("Workflow.setup_schedule_execution()")

        if not self.schedule.startswith('cron') and not self.schedule.startswith('rate'):
            raise APIException(detail=f"Schedule '{self.schedule}' is invalid")

        aws_scheduled_execution_rule_name = f"CR_WF_{self.uuid}"

        client = self.make_events_client(run_environment=run_environment)

        state = 'ENABLED' if self.enabled else 'DISABLED'

        aws_settings = run_environment.parsed_aws_settings()

        if not aws_settings:
            if run_environment.infrastructure_type != INFRASTRUCTURE_TYPE_AWS:
                raise Exception("setup_scheduled_execution(): AWS infrastructure required to schedule workflows")

            aws_settings = cast(AwsSettings, run_environment.parsed_infrastructure_settings())

        if not aws_settings:
            raise Exception("setup_scheduled_execution(): No AWS settings found in Run Environment")

        execution_role_arn = aws_settings.execution_role_arn
        aws_workflow_starter_lambda_arn = aws_settings.workflow_starter_lambda_arn
        aws_workflow_starter_access_key = aws_settings.workflow_starter_access_key

        if not execution_role_arn or (not aws_workflow_starter_lambda_arn) or \
                (not aws_workflow_starter_access_key):
            raise Exception('execution_role_arn, aws_workflow_starter_lambda_arn, aws_workflow_starter_access_key required to schedule Workflows')

        logger.info(f"Using execution role arn = '{execution_role_arn}'")

        # Need this permission: https://github.com/Miserlou/Zappa/issues/381
        # TODO: event bus
        response = client.put_rule(
            Name=aws_scheduled_execution_rule_name,
            ScheduleExpression=self.schedule,
            #EventPattern='true',
            State=state,
            Description=f"Scheduled execution of Workflow {self.uuid}: {self.name}",
            RoleArn=execution_role_arn
        )
            # Tags=[
            #     {
            #         'Key': 'string',
            #         'Value': 'string'
            #     },
            # ],
            # EventBusName='string'


        # TODO: move these somewhere more generic
        self.aws_scheduled_execution_rule_name = aws_scheduled_execution_rule_name
        self.aws_scheduled_event_rule_arn = response['RuleArn']

        logger.info(f"got rule ARN = {self.aws_scheduled_event_rule_arn}")

        if self.enabled:
            client.enable_rule(Name=aws_scheduled_execution_rule_name)
        else:
            client.disable_rule(Name=aws_scheduled_execution_rule_name)

        aws_event_target_rule_name = f"CR_WF_{self.uuid}"
        aws_event_target_id = f"CR_WF_{self.uuid}"

        request_body_dict = {
            'workflow': {
                'uuid': str(self.uuid)
            },
            'status': Execution.Status.MANUALLY_STARTED.name,
            'run_reason': WorkflowExecution.RunReason.SCHEDULED_START.name,
        }

        request = get_request()

        user: User | None = None

        if request:
            user = request.user

        if not user:
            user = self.created_by_user or run_environment.created_by_user

        # TODO: use less privilege
        if request and request.auth and hasattr(request.auth, 'key'):
            token = request.auth.key
        else:
            token_qs = SaasToken.objects.filter(group=self.created_by_group,
                    access_level__gte=UserGroupAccessLevel.ACCESS_LEVEL_TASK)

            if user:
                token_qs = token_qs.filter(user=user)

            # Can't use get_or_create() because there could be duplicates
            saas_token = token_qs.first()

            if not saas_token:
                saas_token = SaasToken(name='Workflow Trigger',
                        description='Used to trigger Workflows',
                        user=user, group=self.created_by_group,
                        access_level=UserGroupAccessLevel.ACCESS_LEVEL_TASK)
                saas_token.save()

            token = saas_token.key

        external_base_url = settings.EXTERNAL_BASE_URL
        input_dict = {
            'request_url': external_base_url + 'api/v1/workflow_executions/',
            'request_method': 'POST',
            'request_headers': {
                'Authorization': 'Token ' + token,
                'X-Url-Requester-Access-Key': run_environment.aws_workflow_starter_access_key
            },
            'request_body': json.dumps(request_body_dict)
        }

        response = client.put_targets(
            Rule=aws_event_target_rule_name,
            Targets=[
                {
                    'Id': aws_event_target_id,
                    'Arn': aws_workflow_starter_lambda_arn,
                    'Input': json.dumps(input_dict)
                },
            ]
        )
        handle_aws_multiple_failure_response(response)

        self.aws_event_target_rule_name = aws_event_target_rule_name
        self.aws_event_target_id = aws_event_target_id
        self.scheduling_run_environment = run_environment


    @override
    def teardown_scheduled_execution(self, run_environment: Optional[RunEnvironment] = None) -> None:
        run_environment = run_environment or self.run_environment_for_scheduling(fallback_to_tasks=False)

        if run_environment is None:
            raise serializers.ValidationError({
                'scheduling_run_environment': ['A Run Environment is required to un-schedule Workflows']
            })

        client = None
        if self.aws_event_target_rule_name and self.aws_event_target_id:
            client = self.make_events_client(run_environment=run_environment)

            try:
                response = client.remove_targets(
                    Rule=self.aws_event_target_rule_name,
                    #EventBusName='string',
                    Ids=[
                        self.aws_event_target_id
                    ],
                    Force=False
                )
                handle_aws_multiple_failure_response(response)
                self.aws_event_target_rule_name = ''
                self.aws_event_target_id = ''
            except ClientError as client_error:
                error_code = client_error.response['Error']['Code']
                # Happens if the schedule rule is removed manually
                if error_code == 'ResourceNotFoundException':
                    logger.warning(f"teardown_scheduled_execution(): Can't remove target {self.aws_event_target_rule_name} because resource not found, exception = {client_error}")
                else:
                    logger.exception(f"teardown_scheduled_execution(): Can't remove target {self.aws_event_target_rule_name} due to unhandled error {error_code}")
                    raise client_error

        if self.aws_scheduled_execution_rule_name:
            client = client or self.make_events_client(run_environment=run_environment)

            try:
                client.delete_rule(
                    Name=self.aws_scheduled_execution_rule_name,
                    #EventBusName='string'
                    Force=True
                )
            except ClientError as client_error:
                error_code = client_error.response['Error']['Code']
                # Happens if the schedule rule is removed manually
                if error_code == 'ResourceNotFoundException':
                    logger.warning(
                      f"teardown_scheduled_execution(): Can't delete rule{self.aws_scheduled_execution_rule_name} because resource not found, exception = {client_error}")
                else:
                    logger.exception(
                        f"teardown_scheduled_execution(): Can't delete rule {self.aws_scheduled_execution_rule_name} due to unhandled error {error_code}")
                    raise client_error

            self.aws_scheduled_event_rule_arn = ''

    def make_events_client(self, run_environment: RunEnvironment):
        return run_environment.make_boto3_client('events')

    def run_environment_for_scheduling(self, fallback_to_tasks: bool=True) -> Optional[RunEnvironment]:
        if self.scheduling_run_environment and \
                self.scheduling_run_environment.can_schedule_workflow():
            return self.scheduling_run_environment

        if self.run_environment and \
                self.run_environment.can_schedule_workflow():
            return self.run_environment

        # workflow_task_instances() can't be called unless the Workflow is saved
        if fallback_to_tasks and self.pk:
            logger.info('Looking for a Run Environment suitable for scheduling in Tasks ...')

            for wti in self.workflow_task_instances.all():
                task = wti.task

                if task:
                    run_env = task.run_environment
                    if run_env and run_env.can_schedule_workflow():
                        return run_env

            logger.info('No suitable Run Environment found for scheduling in Tasks')

        logger.info("No Run Environment found for scheduling")

        return None


@receiver(pre_save, sender=Workflow)
def pre_save_workflow(sender: Type[Workflow], **kwargs) -> None:
    instance = kwargs['instance']
    logger.info(f"pre_save_workflow with Workflow {instance}")

    old_instance: Optional[Workflow] = None
    if instance.pk is None:
        old_instance = None
        usage_limits = Subscription.compute_usage_limits(instance.created_by_group)
        max_workflows = usage_limits.max_workflows

        existing_count = Workflow.objects.filter(
                created_by_group=instance.created_by_group).count()

        if (max_workflows is not None) and (existing_count >= max_workflows):
            raise UnprocessableEntity(detail='Workflow limit exceeded', code='limit_exceeded')
    else:
        old_instance = Workflow.objects.filter(id=instance.id).first()

    should_update_schedule = bool(instance.schedule)

    effective_run_env_for_scheduling: Optional[RunEnvironment] = None

    if instance.schedule:
        effective_run_env_for_scheduling = instance.run_environment_for_scheduling()

    old_effective_run_env_for_scheduling: Optional[RunEnvironment] = None
    run_env_for_scheduling_changed = False
    if old_instance and old_instance.schedule:
        old_effective_run_env_for_scheduling = old_instance.run_environment_for_scheduling(
                fallback_to_tasks=False)
        run_env_for_scheduling_changed = (effective_run_env_for_scheduling != old_effective_run_env_for_scheduling)

        should_update_schedule = (instance.schedule != old_instance.schedule) or \
                (instance.enabled != old_instance.enabled) or run_env_for_scheduling_changed

        if not should_update_schedule:
            for attr in Workflow.AWS_SCHEDULE_ATTRIBUTES:
                new_value = getattr(instance, attr)
                old_value = getattr(old_instance, attr)

                if new_value != old_value:
                    logger.info(f"{attr} changed from {old_value} to {new_value}, adjusting schedule")
                    should_update_schedule = True

    if should_update_schedule:
        logger.info("Updating schedule params ...")

        updated = False
        torn_down = False

        if run_env_for_scheduling_changed and old_effective_run_env_for_scheduling and \
                old_instance and old_instance.schedule:
            instance.teardown_scheduled_execution(run_environment=old_effective_run_env_for_scheduling)
            torn_down = True
            updated = True

        if instance.schedule:
            if effective_run_env_for_scheduling is None:
                raise serializers.ValidationError({
                    'schedule': ['A Run Environment is required to schedule Workflows']
                })

            instance.setup_scheduled_execution(run_environment=effective_run_env_for_scheduling)
            updated = True
        elif old_instance and old_instance.schedule:
            if torn_down:
                logger.info("Skipping redundant teardown")
            elif old_effective_run_env_for_scheduling:
                # Update the fields in instance, but use the previous scheduling_run_environment
                instance.teardown_scheduled_execution(
                    run_environment=old_effective_run_env_for_scheduling)
                updated = True
            else:
                logger.warning("No scheduling_run_environment can be used teardown")
        elif not torn_down:
            logger.warning("should_update_schedule is True, but not setting up or tearing down")

        if updated:
            instance.schedule_updated_at = timezone.now()
            logger.info("Done updating schedule params ...")
    else:
        logger.info("Not updating schedule params")


@receiver(pre_delete, sender=Workflow)
def pre_delete_workflow(sender: Type[Workflow], **kwargs) -> None:
    instance = kwargs['instance']
    logger.info(f"pre_delete_workflow with workflow {instance}")

    if instance.schedule:
        instance.teardown_scheduled_execution()

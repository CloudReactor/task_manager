from typing import Any, FrozenSet, Optional, Tuple, TYPE_CHECKING

import logging
import enum

from rest_framework.exceptions import (
    APIException,
    ValidationError
)

from ..common.request_helpers import context_with_request
from ..common.utils import coalesce
from ..exception import UnprocessableEntity

if TYPE_CHECKING:
    from ..models import (
      Task,
      TaskExecution
    )

logger = logging.getLogger(__name__)


class ExecutionMethod:
    @enum.unique
    class ExecutionCapability(enum.IntEnum):
        MANUAL_START = 1
        SCHEDULING = 2
        SETUP_SERVICE = 3

    ALL_CAPABILITIES = frozenset([
        ExecutionCapability.MANUAL_START,
        ExecutionCapability.SCHEDULING,
        ExecutionCapability.SETUP_SERVICE
    ])

    TASK_FIELDS_IN_CONTEXT = [
        'uuid', 'name',
        #'url', 'description', 'dashboard_url',
        'max_manual_start_delay_before_alert_seconds',
        'max_manual_start_delay_before_abandonment_seconds',
        'heartbeat_interval_seconds',
        'max_heartbeat_lateness_before_alert_seconds',
        'max_heartbeat_lateness_before_abandonment_seconds',
        'schedule', 'scheduled_instance_count',
        'is_service', 'service_instance_count',
        'min_service_instance_count',
        'max_concurrency',
        'max_age_seconds', 'default_max_retries',
        #'max_postponed_failure_count', 'max_postponed_missing_execution_count',
        #'max_postponed_timeout_count',
        'min_missing_execution_delay_seconds',
        #'postponed_failure_before_success_seconds',
        #'postponed_missing_execution_before_start_seconds',
        #'postponed_timeout_before_success_seconds',
        'project_url',
        #'log_query', 'logs_url',
        #'links',
        'run_environment',
        'allocated_cpu_units',
        'allocated_memory_mb',
        #'execution_method_capability', # Deprecated
        'execution_method_type',
        'execution_method_capability_details',
        #'capabilities',
        'infrastructure_type',
        'infrastructure_settings',
        #'scheduling_provider_type',
        #'scheduling_settings',
        #'service_provider_type',
        #'service_settings',
        #'notification_profiles',
        'other_metadata',
        #'latest_task_execution',
        #'created_by_user', 'created_by_group',
        'was_auto_created', 'passive', 'enabled',
        'created_at', 'updated_at',
    ]

    TASK_EXECUTION_FIELDS_IN_CONTEXT = [
        'uuid',
        'status', 'run_reason',
        'task_version_number', 'task_version_signature', 'task_version_text',
        'other_instance_metadata',
        'started_at',
        'created_at', 'updated_at',
    ]

    WORKFLOW_EXECUTION_FIELDS_IN_CONTEXT = [
        #'url',
        'uuid',
        #'dashboard_url',
        'status', 'run_reason',
        'started_at',
        #'finished_at', 'last_heartbeat_at',
        #'stop_reason', 'marked_done_at',
        #'kill_started_at', 'kill_finished_at',
        #'kill_error_code',
        'failed_attempts', 'timed_out_attempts',
        'created_at', 'updated_at',
    ]

    def __init__(self, name: str,
            task: Optional['Task'],
            task_execution: Optional['TaskExecution']):
        self.name = name
        self.task_execution = task_execution

        if task_execution and (task is None):
            task = task_execution.task

        self.task = task

    def capabilities(self) -> FrozenSet[ExecutionCapability]:
        return frozenset()

    def supports_capability(self, cap: ExecutionCapability) -> bool:
        return cap in self.capabilities()

    def should_update_or_force_recreate_scheduled_execution(self,
            old_execution_method: Optional['ExecutionMethod']=None) -> Tuple[bool, bool]:
        should = self.should_maybe_update_scheduled_execution(
                  old_execution_method=old_execution_method)
        return (coalesce(should, True), False)

    def setup_scheduled_execution(self,
            old_execution_method: Optional['ExecutionMethod']=None,
            force_creation: bool=False, teardown_result: Optional[Any]=None) -> None:
        raise UnprocessableEntity(
                detail='Execution method does not support scheduled execution.')

    def teardown_scheduled_execution(self) -> Tuple[Optional[dict[str, Any]], Optional[Any]]:
        logger.warning('teardown_service(): execution method does not support scheduled execution, no-op')
        return (None, None)

    def should_update_or_force_recreate_service(self,
            old_execution_method: Optional['ExecutionMethod']=None) \
            -> Tuple[bool, bool]:
        return (False, False)

    def setup_service(self,
            old_execution_method: Optional['ExecutionMethod'] = None,
            force_creation: bool=False, teardown_result: Optional[Any]=None) -> None:
        raise UnprocessableEntity(
                detail='Execution method does not support service setup.')

    def teardown_service(self) -> Tuple[Optional[dict[str, Any]], Optional[Any]]:
        logger.info('teardown_service(): execution method does not support services, no-op')
        return (None, None)

    def manually_start(self) -> None:
        raise ValidationError(detail='Execution method does not support manual start.')

    # TODO: allow implementation to partially fail, signaling errors
    def enrich_task_settings(self) -> None:
        pass

    # TODO: allow implementation to partially fail, signaling errors
    def enrich_task_execution_settings(self) -> None:
        pass

    def make_context(self) -> dict[str, Any]:
        from ..models import (
            WorkflowTaskInstanceExecution
        )
        from ..serializers import (
            TaskSerializer, TaskExecutionSerializer,
            WorkflowExecutionSummarySerializer
        )

        task_execution = self.task_execution

        if not task_execution:
            raise APIException("Missing Task Execution")

        task = self.task or task_execution.task

        te_uuid = task_execution.uuid

        serializer_context = context_with_request()

        task_info: dict[str, Any] = TaskSerializer(task,
                context=serializer_context,
                fields=self.TASK_FIELDS_IN_CONTEXT).data

        #     'uuid': str(task.uuid),
        #     'name': task.name,
        #     'run_environment': {
        #         'uuid': str(run_env.uuid),
        #         'name': str(run_env.name),
        #     },
        #     'other_metadata': task.other_metadata,
        #     'was_auto_created': task.was_auto_created,
        #     'passive': task.passive
        # }

        wtie = WorkflowTaskInstanceExecution.objects.filter(
          task_execution__uuid=te_uuid).first()

        wtie_info: Optional[dict[str, Any]] = None

        if wtie:
            workflow_execution = wtie.workflow_execution
            we_info = WorkflowExecutionSummarySerializer(workflow_execution,
                context=serializer_context,
                fields=self.WORKFLOW_EXECUTION_FIELDS_IN_CONTEXT).data

            # {
            #     'workflow': workflow_info,
            #     'status': Execution.Status(workflow_execution.status).name,
            #     'run_reason': we_run_reason,
            #     'started_at': workflow_execution.started_at.replace(microsecond=0).isoformat(),
            #     'failed_attempts': workflow_execution.failed_attempts,
            #     'timed_out_attempts': workflow_execution.timed_out_attempts
            # }

            wti = wtie.workflow_task_instance
            wti_info = {
                'uuid': str(wti.uuid),
                'name': wti.name,
                'start_transition_condition': wti.start_transition_condition,
                'max_age_seconds': wti.max_age_seconds,
                'default_max_retries': wti.default_max_retries,
                'allow_workflow_execution_after_failure': wti.allow_workflow_execution_after_failure
            }

            wtie_info = {
                'uuid': str(wtie.uuid),
                'workflow_execution': we_info,
                'workflow_task_instance': wti_info
            }

        task_execution_info = TaskExecutionSerializer(task_execution,
            context=serializer_context,
            fields=self.TASK_EXECUTION_FIELDS_IN_CONTEXT).data

        # task_execution_info: dict[str, Any] = {
        #     'uuid': str(te_uuid),
        #     'status': TaskExecution.Status(task_execution.status).name,
        #     'run_reason': run_reason_str,
        #     'task_version_number': task_execution.task_version_number,
        #     'task_version_signature': task_execution.task_version_signature,
        #     'task_version_text': task_execution.task_version_text,
        #     'other_instance_metadata': task_execution.other_instance_metadata,
        #     'started_at': task_execution.started_at.replace(microsecond=0).isoformat(),
        #     'task': task_info,
        #     'workflow_task_instance_execution': wtie_info
        # }

        task_execution_info['task'] = task_info
        task_execution_info['workflow_task_instance_execution'] = wtie_info

        return {
            'task_execution': task_execution_info,
            'env_override': task_execution.make_environment()
        }

    @staticmethod
    def make_execution_method(task: Optional['Task'] = None,
            task_execution: Optional['TaskExecution'] = None) -> 'ExecutionMethod':
        from .aws_codebuild_execution_method import AwsCodeBuildExecutionMethod
        from .aws_ecs_execution_method import AwsEcsExecutionMethod
        from .aws_lambda_execution_method import AwsLambdaExecutionMethod
        from .unknown_execution_method import UnknownExecutionMethod

        emt = UnknownExecutionMethod.NAME

        if task_execution and (not task):
            task = task_execution.task

        if task:
            emt = task.execution_method_type
            logger.debug(f"task emt = {emt}")

        if task_execution:
            emt = task_execution.execution_method_type or emt
            logger.info(f"emt overridden to = {emt}")

        if emt == AwsEcsExecutionMethod.NAME:
            return AwsEcsExecutionMethod(task=task, task_execution=task_execution)
        elif emt == AwsLambdaExecutionMethod.NAME:
            return AwsLambdaExecutionMethod(task=task, task_execution=task_execution)
        elif emt == AwsCodeBuildExecutionMethod.NAME:
            return AwsCodeBuildExecutionMethod(task=task, task_execution=task_execution)
        return UnknownExecutionMethod(task=task, task_execution=task_execution)

    def should_maybe_update_scheduled_execution(self,
            old_execution_method: Optional['ExecutionMethod']) -> Optional[bool]:
        if self.task is None:
            raise APIException('should_maybe_update_scheduled_execution() without Task')

        should_schedule = self.task.has_active_managed_scheduled_execution(current=False)

        if old_execution_method is None:
            return should_schedule

        old_task = old_execution_method.task

        if not old_task:
            return should_schedule

        was_scheduled = old_task.has_active_managed_scheduled_execution()

        if should_schedule != was_scheduled:
            return True

        if (not should_schedule) and (not was_scheduled):
            return False

        if (self.task.schedule != old_task.schedule) or \
                (self.task.scheduling_provider_type != old_task.scheduling_provider_type) or \
                (self.task.scheduled_instance_count != old_task.scheduled_instance_count):
            return True

        return None

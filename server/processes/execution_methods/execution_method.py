from typing import Any, FrozenSet, Optional, TYPE_CHECKING

import logging
import enum

from rest_framework.exceptions import ValidationError

from ..common.request_helpers import context_with_request
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
        #'infrastructure_website_url',
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
        #'should_clear_failure_alerts_on_success',
        #'should_clear_timeout_alerts_on_success',
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
        #'alert_methods',
        'other_metadata',
        #'latest_task_execution',
        #'current_service_info', # Deprecated
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

    def __init__(self, name: str, task: 'Task'):
        self.name = name
        self.task = task

    def capabilities(self) -> FrozenSet[ExecutionCapability]:
        return frozenset()

    def supports_capability(self, cap: ExecutionCapability) -> bool:
        return cap in self.capabilities()

    def setup_scheduled_execution(self) -> None:
        raise UnprocessableEntity(
                detail='Execution method does not support scheduled execution.')

    def teardown_scheduled_execution(self) -> None:
        logger.info('teardown_service(): execution method does not support scheduled execution, no-op')

    def setup_service(self, force_creation=False) -> None:
        raise UnprocessableEntity(
                detail='Execution method does not support service setup.')

    def teardown_service(self) -> None:
        logger.info('teardown_service(): execution method does not support services, no-op')

    def manually_start(self, task_execution: 'TaskExecution') -> None:
        raise ValidationError(detail='Execution method does not support manual start.')

    def enrich_task_settings(self) -> None:
        pass

    def make_context(self, task_execution: 'TaskExecution') -> dict[str, Any]:
      from ..models import (
          WorkflowTaskInstanceExecution
      )
      from ..serializers import (
          TaskSerializer, TaskExecutionSerializer,
          WorkflowExecutionSummarySerializer
      )

      te_uuid = task_execution.uuid
      task = task_execution.task

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
          #     'status': WorkflowExecution.Status(workflow_execution.status).name,
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

      task_execution_info['task'] = task_info,
      task_execution_info['workflow_task_instance_execution'] = wtie_info

      return {
          'task_execution': task_execution_info,
          'env_override': task_execution.make_environment()
      }

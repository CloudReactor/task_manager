from typing import Any, Mapping, Optional, cast

import logging

from django.conf import settings
from django.utils import timezone

from rest_framework import serializers
from rest_framework import status as rfstatus
from rest_framework.exceptions import ErrorDetail, NotFound

from rest_flex_fields.serializers import FlexFieldsSerializerMixin

from drf_spectacular.utils import extend_schema_field

from ..models import (
    Task, TaskExecution, UserGroupAccessLevel,
    WorkflowTaskInstanceExecution
)

from ..common import (
    extract_authenticated_run_environment
)
from ..common.request_helpers import ensure_group_access_level
from ..exception import UnprocessableEntity
from ..execution_methods import *

from .name_and_uuid_serializer import NameAndUuidSerializer

from .embedded_id_validating_serializer_mixin import (
    EmbeddedIdValidatingSerializerMixin
)

from .serializer_helpers import SerializerHelpers
from .aws_ecs_execution_method_serializer import AwsEcsExecutionMethodSerializer
from .unknown_execution_method_serializer import UnknownExecutionMethodSerializer
from .workflow_task_instance_execution_base_serializer import WorkflowTaskInstanceExecutionBaseSerializer

logger = logging.getLogger(__name__)


@extend_schema_field(field=serializers.ChoiceField(choices=[
        status.name for status in list(TaskExecution.Status)]),
        component_name='TaskExecutionStatus')
class TaskExecutionStatusSerializer(serializers.BaseSerializer):
    def to_representation(self, instance: TaskExecution.Status) -> str:
        return TaskExecution.Status(instance).name

    def to_internal_value(self, data: str) -> int:
        return TaskExecution.Status[data.upper()].value


@extend_schema_field(serializers.ChoiceField(choices=[
        reason.name for reason in list(TaskExecution.StopReason)]))
class TaskExecutionStopReasonSerializer(serializers.BaseSerializer):
    def to_representation(self, instance: TaskExecution.StopReason) -> str:
        return TaskExecution.StopReason(instance).name

    def to_internal_value(self, data: str) -> int:
        return TaskExecution.StopReason[data.upper()].value


class TaskExecutionSerializer(EmbeddedIdValidatingSerializerMixin,
        FlexFieldsSerializerMixin,
        SerializerHelpers,
        serializers.HyperlinkedModelSerializer):
    """
    A Task Execution is an execution / run instance of a Task.
    """

    class Meta:
        model = TaskExecution
        fields = ('url',
                  'uuid', 'dashboard_url', 'infrastructure_website_url',
                  'task',
                  'task_version_number', 'task_version_text',
                  'task_version_signature', 'commit_url',
                  'other_instance_metadata',
                  'hostname',
                  'environment_variables_overrides',
                  'execution_method', 'status',
                  'started_by', 'started_at',
                  'finished_at',
                  'marked_done_by',
                  'marked_done_at',
                  'marked_outdated_at',
                  'killed_by',
                  'kill_started_at', 'kill_finished_at',
                  'kill_error_code',
                  'stop_reason',
                  'last_heartbeat_at',
                  'failed_attempts', 'timed_out_attempts',
                  'exit_code', 'last_status_message',
                  'error_count', 'skipped_count',
                  'expected_count', 'success_count',
                  'other_runtime_metadata',
                  'current_cpu_units', 'mean_cpu_units', 'max_cpu_units',
                  'current_memory_mb', 'mean_memory_mb', 'max_memory_mb',
                  'wrapper_version', 'wrapper_log_level',
                  'deployment', 'process_command', 'is_service',
                  'task_max_concurrency', 'max_conflicting_age_seconds',
                  'prevent_offline_execution',
                  'process_timeout_seconds', 'process_termination_grace_period_seconds',
                  'process_max_retries', 'process_retry_delay_seconds',
                  'schedule',
                  'heartbeat_interval_seconds',
                  'workflow_task_instance_execution',
                  'api_base_url', # Don't expose api_key
                  'api_request_timeout_seconds',
                  'api_retry_delay_seconds',
                  'api_resume_delay_seconds',
                  'api_error_timeout_seconds',
                  'api_task_execution_creation_error_timeout_seconds',
                  'api_task_execution_creation_conflict_timeout_seconds',
                  'api_task_execution_creation_conflict_retry_delay_seconds',
                  'api_final_update_timeout_seconds',
                  'status_update_interval_seconds',
                  'status_update_port', 'status_update_message_max_bytes',
                  'debug_log_tail', 'error_log_tail',
                  'embedded_mode',
                  'created_at', 'updated_at',)

        read_only_fields = [
            'url', 'uuid', 'dashboard_url', 'infrastructure_website_url',
            'created_by_user', 'created_by_group',
            'created_at', 'updated_at'
        ]

    # required=False so that legacy proc_wrappers can use "process_type"
    task = NameAndUuidSerializer(view_name='tasks-detail', required=False)

    started_by = serializers.ReadOnlyField(source='started_by.username')
    marked_done_by = serializers.ReadOnlyField(
        source='marked_done_by.username', allow_null=True)
    killed_by = serializers.ReadOnlyField(source='killed_by.username',
        allow_null=True)
    url = serializers.HyperlinkedIdentityField(
        view_name='task_executions-detail',
        lookup_field='uuid'
    )
    execution_method = serializers.SerializerMethodField()
    status = TaskExecutionStatusSerializer()
    stop_reason = TaskExecutionStopReasonSerializer(required=False,
        allow_null=True)
    commit_url = serializers.ReadOnlyField(allow_null=True)
    workflow_task_instance_execution = serializers.SerializerMethodField(
        allow_null=True)

    def validate(self, attrs: Mapping[str, Any]) -> Mapping[str, Any]:
        attrs = super().validate(attrs)

        status = attrs.get('status')

        if status == TaskExecution.Status.MANUALLY_STARTED:
            data_task = attrs.get('task')

            if data_task is None:
                if self.instance:
                    task_execution = cast(TaskExecution, self.instance)
                    task = task_execution.task
                else:
                    raise serializers.ValidationError({
                        'task': [
                            ErrorDetail('Missing Task', code='missing')
                        ]
                    })
            else:
                # checkme: dict to Task?
                task = cast(Task, data_task)

            if task.passive:
                raise serializers.ValidationError({
                    'status': [
                        ErrorDetail('Passive Tasks may be not manually started',
                                code='invalid')
                    ]
                })

        return attrs

    def to_internal_value(self, data: Mapping[str, Any]):
        # Remove process_version and process_hash once all process wrapper scripts < 1.2.0 are extinct
        process_version_number = data.get('process_version_number',
                                   data.get('process_version'))

        if process_version_number is not None:
            data['task_version_number'] = process_version_number

        process_version_signature = data.get('process_version_signature',
            data.get('process_hash'))

        if process_version_signature:
            data['task_version_signature'] = process_version_signature
        # End legacy

        # Remove once wrappers < 2.0 are extinct
        api_request_timeout_seconds = data.get('api_timeout_seconds')
        if api_request_timeout_seconds is not None:
            data['api_request_timeout_seconds'] = api_request_timeout_seconds
        # End < 2.0

        validated = super().to_internal_value(data)

        logger.info(f"super validated = {validated}")

        group = self.get_request_group()

        # Support process_type for backward compatibility with wrapper scripts
        # less than 2.0.0
        task_dict = data.get('task') or data.get('process_type')

        if task_dict is None:
            if ('task' in data) or ('process_type' in data):
                raise serializers.ValidationError({
                    'task': [ErrorDetail('Cannot be empty', code='invalid')]
                })
        else:
            authenticated_run_environment = extract_authenticated_run_environment()
            was_auto_created = task_dict.get('was_auto_created')
            task: Optional[Task] = None
            try:
                task = Task.find_by_uuid_or_name(
                    task_dict, required_group=group,
                    required_run_environment=authenticated_run_environment)
            except (Task.DoesNotExist, NotFound) as e:
                if was_auto_created:
                    from .task_serializer import TaskSerializer
                    task_serializer = TaskSerializer(task, data=task_dict,
                            context=self.context)
                    task_serializer.is_valid(raise_exception=True)
                    task = task_serializer.save()
                else:
                    raise UnprocessableEntity({
                        'task': [ErrorDetail('Task does not exist', code='not_found')]
                    }) from e

            logger.debug(f"to_internal_value(): validated task {task}")

            validated['task'] = task

        validated['started_by'] = self.get_request_user()

        execution_method_dict = data.get('execution_method')

        if execution_method_dict:
            self.copy_props_with_prefix(dest_dict=validated,
                  src_dict=execution_method_dict,
                  included_keys=['allocated_cpu_units',
                      'allocated_memory_mb'])

            self.copy_props_with_prefix(dest_dict=validated,
                  src_dict=execution_method_dict,
                  dest_prefix='aws_ecs_',
                  included_keys=[
                      'task_definition_arn', 'task_arn', 'launch_type',
                      'cluster_arn', 'security_groups',
                      'assign_public_ip', 'execution_role',
                      'task_role', 'platform_version',
                  ])

        return validated

    def create(self, validated_data: Mapping[str, Any]):
        now = timezone.now()

        request_status = TaskExecution.Status(validated_data.get(
            'status', TaskExecution.Status.RUNNING))

        logger.info(f"create: request status = {request_status.name}")

        if request_status == TaskExecution.Status.RUNNING:
            if not validated_data.get('last_heartbeat_at'):
                validated_data['last_heartbeat_at'] = now
        elif request_status in [TaskExecution.Status.SUCCEEDED,
                TaskExecution.Status.FAILED, TaskExecution.Status.ABORTED,
                TaskExecution.Status.TERMINATED_AFTER_TIME_OUT,
                TaskExecution.Status.EXITED_AFTER_MARKED_DONE]:
            if 'finished_at' not in validated_data:
                validated_data['finished_at'] = now

        self.protect_attributes(validated_data=validated_data,
                existing_task_execution=None,
                task=cast(Task, validated_data['task']))

        self.update_api_client_implicit_info(validated_data=validated_data)

        return super().create(validated_data)

    def update(self, instance, validated_data: Mapping[str, Any]):
        now = timezone.now()

        logger.info(
            f"calling update with existing instance {instance}, validated {validated_data}")

        validated_task = validated_data.pop('task', None)

        # Support process_type for backward compatibility
        if validated_task is None:
            validated_task = validated_data.get('process_type')

        if validated_task:
            if instance.task != validated_task:
                raise UnprocessableEntity({
                    'task': [ErrorDetail('Does not match existing', code='invalid')]
                })

            validated_data['task'] = validated_task

        request_status = TaskExecution.Status(validated_data.get(
                'status', TaskExecution.Status.RUNNING))
        existing_status = TaskExecution.Status(instance.status)

        if request_status == TaskExecution.Status.RUNNING:
            if existing_status == TaskExecution.Status.STOPPING:
                # We'll be returning a 409 status code. Assume the Task will stop. In the future,
                # implement a handshake for wrapper scripts. For those versions that implement
                # the handshake we'll leave the status STOPPING until the script sends
                # acknowledgment with a EXITED_AFTER_MARKED_DONE status, or something similar.
                validated_data['status'] = TaskExecution.Status.STOPPED
            elif existing_status not in TaskExecution.IN_PROGRESS_STATUSES:
                validation_error = serializers.ValidationError(
                    {'status': f"Status cannot be set to {request_status.name} after {existing_status.name}"})
                validation_error.status_code = rfstatus.HTTP_409_CONFLICT
                raise validation_error

            if 'last_heartbeat_at' not in validated_data:
                validated_data['last_heartbeat_at'] = now
        elif request_status in (TaskExecution.Status.SUCCEEDED,
                TaskExecution.Status.FAILED,
                TaskExecution.Status.TERMINATED_AFTER_TIME_OUT,
                TaskExecution.Status.ABORTED):
            logger.info(f"old status = {existing_status.name}")

            if existing_status not in (request_status,
                    TaskExecution.Status.RUNNING,
                    TaskExecution.Status.MANUALLY_STARTED,
                    TaskExecution.Status.STOPPING):
                validation_error = serializers.ValidationError(
                    {'status': f"Status cannot be set to {request_status.name} after {existing_status.name}"})
                validation_error.status_code = rfstatus.HTTP_409_CONFLICT
                raise validation_error

            if (request_status in (TaskExecution.Status.FAILED,
                    TaskExecution.Status.ABORTED)) \
                    and (existing_status == TaskExecution.Status.STOPPING):
                logger.info(f"Overriding status from {request_status.name} to STOPPED since existing status was STOPPING")
                validated_data['status'] = TaskExecution.Status.STOPPED

            if ('finished_at' not in validated_data) and (not instance.finished_at):
                validated_data['finished_at'] = now

        for attr in TaskExecution.UNMODIFIABLE_ATTRIBUTES:
            if getattr(instance, attr) is not None:
                validated_data.pop(attr, None)

        task_execution = cast(TaskExecution, self.instance)
        self.protect_attributes(validated_data=validated_data,
            existing_task_execution=task_execution,
            task=task_execution.task)

        self.update_api_client_implicit_info(validated_data=validated_data)

        return super().update(instance, validated_data)

    # TODO: output raw JSON
    @extend_schema_field(AwsEcsExecutionMethodSerializer)
    def get_execution_method(self, obj: TaskExecution):
        method_type = obj.task.execution_method_type

        if method_type == AwsEcsExecutionMethod.NAME:
            return AwsEcsExecutionMethodSerializer(obj, source='*',
                    required=False).data
        else:
            return UnknownExecutionMethodSerializer(obj, source='*',
                    required=False).data

    @extend_schema_field(WorkflowTaskInstanceExecutionBaseSerializer)
    def get_workflow_task_instance_execution(self, obj: TaskExecution):
        try:
            wtie = obj.workflowtaskinstanceexecution
        except WorkflowTaskInstanceExecution.DoesNotExist:
            return None

        return WorkflowTaskInstanceExecutionBaseSerializer(wtie,
                context=self.context, read_only=True).data

    def protect_attributes(self, validated_data: Mapping[str, Any],
            existing_task_execution: Optional[TaskExecution],
            task: Task) -> None:
        if task.was_auto_created and task.passive:
            return

        # It's ok to update protected attributes after the Task Execution
        # has started, since they won't be re-used.
        status = validated_data.get('status')
        if (status is None) and existing_task_execution:
            status = existing_task_execution.status

        if status != TaskExecution.Status.MANUALLY_STARTED:
            return

        escalate = False
        for attr in TaskExecution.ATTRIBUTES_REQUIRING_DEVELOPER_ACCESS_FOR_UPDATE:
            if attr in validated_data:
                if existing_task_execution:
                    existing_value = getattr(existing_task_execution, attr)
                    updated_value = validated_data[attr]
                    escalate = (existing_value != updated_value)

                    if escalate:
                        logger.info(f"Escalating access required because attribute '{attr}' changed from '{existing_value}' to '{updated_value}'")
                else:
                    escalate = True
                    logger.info(f"Escalating access required because attribute '{attr}' was present during Task Execution creation")

                if escalate:
                    break

        if not escalate:
            env_override = validated_data.get('environment_variables_overrides')

            if env_override:
                for name in env_override.keys():
                    if name.startswith("PROC_WRAPPER_"):
                        escalate = True
                        logger.info(f"Escalating access required because environment variable '{name}' found in environment.")
                        break

        if escalate:
            ensure_group_access_level(
                group=task.created_by_group,
                min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                run_environment=task.run_environment,
                allow_api_key=True)

    def update_api_client_implicit_info(self, validated_data: dict[str, Any]) -> None:
        validated_data['api_base_url'] = settings.EXTERNAL_BASE_URL.rstrip('/')
        request = self.context['request']
        if request.auth and hasattr(request.auth, 'key'):
            validated_data['api_key'] = request.auth.key

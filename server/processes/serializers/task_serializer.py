from typing import (
    Any, Mapping, Optional,
    Type, Union,
    cast
)

import copy
import logging

from rest_framework import serializers
from rest_framework.exceptions import (
    ErrorDetail, ValidationError
)

from rest_flex_fields.serializers import FlexFieldsSerializerMixin

from drf_spectacular.utils import (
    extend_schema_field,
    PolymorphicProxySerializer,
)

from .aws_ecs_execution_method_capability_serializer import (
    AwsEcsExecutionMethodCapabilitySerializer
)
from .unknown_execution_method_capability_serializer import (
    UnknownExecutionMethodCapabilitySerializer
)

from ..common.request_helpers import required_user_and_group_from_request
from ..execution_methods import *
from ..models import *

from .name_and_uuid_serializer import NameAndUuidSerializer
from .embedded_id_validating_serializer_mixin import (
    EmbeddedIdValidatingSerializerMixin
)

from .serializer_helpers import SerializerHelpers
from .group_setting_serializer_mixin import GroupSettingSerializerMixin
from .task_execution_serializer import TaskExecutionSerializer
from .link_serializer import LinkSerializer

logger = logging.getLogger(__name__)


class CurrentServiceInfoSerializer(serializers.Serializer):
    class Meta:
        model = Task
        fields = ('type', 'service_arn', 'service_infrastructure_website_url',
                'service_arn_updated_at',)

    SERVICE_INFO_TYPE_AWS_ECS = 'AWS ECS'

    type = serializers.SerializerMethodField(method_name='get_service_info_type')

    def get_service_info_type(self, obj) -> str:
        return self.SERVICE_INFO_TYPE_AWS_ECS

    service_arn = serializers.ReadOnlyField(
            source='aws_ecs_service_arn')

    service_infrastructure_website_url = serializers.ReadOnlyField(
            source='aws_ecs_service_infrastructure_website_url')

    service_arn_updated_at = serializers.ReadOnlyField(
            source='aws_ecs_service_updated_at')

# TODO: validate size of other_metadata, allowed ECS launch types
class TaskSerializer(GroupSettingSerializerMixin,
        EmbeddedIdValidatingSerializerMixin,
        FlexFieldsSerializerMixin,
        serializers.HyperlinkedModelSerializer,
        SerializerHelpers):
    """
    A Task is a specification for a runnable job, including details on how to
    run the task and how often the task is supposed to run.
    """

    class Meta:
        model = Task
        fields = ['url',
                  'uuid', 'name', 'description', 'dashboard_url',
                  'infrastructure_website_url',
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
                  'project_url', 'log_query', 'logs_url',
                  'links',
                  'run_environment',
                  'execution_method_capability',
                  'alert_methods',
                  'other_metadata',
                  'latest_task_execution',
                  'current_service_info',
                  'created_by_user', 'created_by_group',
                  'was_auto_created', 'passive', 'enabled',
                  'created_at', 'updated_at',
        ]

        read_only_fields = [
          'url', 'uuid',
          'is_service',
          'latest_task_execution', 'current_service_info',
          'dashboard_url', 'infrastructure_website_url', 'logs_url',
          'created_at', 'updated_at',
        ]

    latest_task_execution = serializers.SerializerMethodField()
    url = serializers.HyperlinkedIdentityField(
        view_name='tasks-detail',
        lookup_field='uuid'
    )
    execution_method_capability = serializers.SerializerMethodField()
    current_service_info = serializers.SerializerMethodField()

    alert_methods = NameAndUuidSerializer(
            include_name=True,
            view_name='alert_methods-detail',
            many=True, required=False)

    links = LinkSerializer(many=True, required=False)

    #Not sure why this doesn't work
    #logs_url = serializers.ReadOnlyField(source='get_logs_url')
    logs_url = serializers.SerializerMethodField()

    @extend_schema_field(TaskExecutionSerializer)
    def get_latest_task_execution(self, obj: Task):
        # Set the process type so we don't get N+1 queries looking back
        # Seems to slow down in ECS even though it stops N+1 queries
        if obj.latest_task_execution:
            obj.latest_task_execution.task = obj

        return TaskExecutionSerializer(instance=obj.latest_task_execution,
                context=self.context, required=False,
                omit='marked_done_by,killed_by').data

    @extend_schema_field(PolymorphicProxySerializer(
          component_name='ExecutionMethodCapability',
          serializers=cast(list[Union[serializers.Serializer, Type[serializers.Serializer]]], [
              AwsEcsExecutionMethodCapabilitySerializer,
              UnknownExecutionMethodCapabilitySerializer
          ]),
          resource_type_field_name='type'
    ))
    def get_execution_method_capability(self, obj: Task):
        method_name = obj.execution_method_type
        return self.execution_method_capability_serializer_for_type(
                method_name=method_name, task=obj).data

    @extend_schema_field(CurrentServiceInfoSerializer(required=False,
            read_only=True))
    def get_current_service_info(self, obj: Task):
        if not obj.is_service:
            return None

        if obj.execution_method_type == AwsEcsExecutionMethod.NAME:
            return CurrentServiceInfoSerializer(instance=obj,
                    context=self.context).data
        return None

    def get_logs_url(self, obj: Task) -> Optional[str]:
        return obj.logs_url()

    def validate(self, attrs: Mapping[str, Any]) -> Mapping[str, Any]:
        task: Optional[Task] = None
        if self.instance:
            task = cast(Task, self.instance)

        passive = attrs.get('passive')
        if (passive is None) and task:
            passive = task.passive

        if passive is None:
            passive = False

        execution_method_type = attrs.get('execution_method_type',
                task.execution_method_type if task \
                else UnknownExecutionMethod.NAME)

        if (not passive) and (execution_method_type == UnknownExecutionMethod.NAME):
            raise ValidationError({
                'passive': [ErrorDetail('Non-passive Tasks may not have an Unknown execution method',
                        code='invalid')]
            })

        return attrs

    def to_internal_value(self, data):
        body_task_links = data.pop('links', None) or \
            data.pop('process_type_links', None)

        validated = super().to_internal_value(data)

        user, group = required_user_and_group_from_request()

        task: Optional[Task] = cast(Task, self.instance) if self.instance else None

        run_environment = validated.get('run_environment',
            task.run_environment if task else None)

        if run_environment is None:
            raise ValidationError({
                'run_environment': ErrorDetail('Run Environment is required', 'missing')
            })

        # Not sure why is_service isn't in validated even when specified in the
        # request body, falling back to original request.
        is_service = validated.pop('is_service', data.get('is_service'))
        service_instance_count = validated.get('service_instance_count')
        min_service_instance_count = validated.get('min_service_instance_count')
        schedule = validated.get('schedule')

        if (min_service_instance_count is not None) \
                and (min_service_instance_count > 0):
            if is_service is False:
                raise serializers.ValidationError({
                    'min_service_instance_count': ['Must null for services']
                })
            is_service = True

        if (service_instance_count is not None) and (service_instance_count > 0):
            if is_service is False:
                raise serializers.ValidationError({
                    'service_instance_count': ['Must null for services']
                })
            is_service = True

        if (is_service is None) and schedule:
            is_service = False

        if (is_service is None) and task:
            is_service = task.is_service

        if is_service:
            if schedule:
                raise serializers.ValidationError({
                    'schedule': ['Must be blank for services']
                })

            if service_instance_count is None:
                if task:
                    service_instance_count = task.service_instance_count

                if service_instance_count is None:
                    service_instance_count = min_service_instance_count or 1

            if service_instance_count <= 0:
                raise serializers.ValidationError({
                    'service_instance_count': ['Must be positive for services']
                })

            if min_service_instance_count is None:
                if task:
                    min_service_instance_count = task.min_service_instance_count

                if min_service_instance_count is None:
                    min_service_instance_count = service_instance_count

            if min_service_instance_count > service_instance_count:
                raise serializers.ValidationError({
                    'min_service_instance_count': ['Must be less than or equal to service_instance_count']
                })

            validated['schedule'] = ''
            validated['min_service_instance_count'] = min_service_instance_count
            validated['service_instance_count'] = service_instance_count
        else:
            if service_instance_count and (service_instance_count > 0):
                raise serializers.ValidationError({
                    'service_instance_count': ['Must be null or zero for non-services']
                })

            if min_service_instance_count and (min_service_instance_count > 0):
                raise serializers.ValidationError({
                    'min_service_instance_count': ['Must be non-positive if service_instance_count is negative']
                })

            validated['min_service_instance_count'] = None
            validated['service_instance_count'] = None

        validated['is_service'] = is_service

        execution_method_dict = data.get('execution_method_capability')

        execution_method_type = task.execution_method_type if task else \
                UnknownExecutionMethod.NAME

        if execution_method_dict:
            execution_method_type = execution_method_dict.get('type',
                    execution_method_type)

            validated['execution_method_type'] = execution_method_type

            logger.debug(f"{execution_method_dict=}")
            logger.debug(f"{execution_method_type=}")

            ems = self.execution_method_capability_serializer_for_type(
                    method_name=execution_method_type, task=task,
                    is_service=is_service, run_environment=run_environment)

            em_validated = ems.to_internal_value(execution_method_dict)

            logger.debug(f"{em_validated=}")

            validated |= em_validated

            # Execution method serializer may set is_service if it was None
            is_service = validated['is_service']

        self.set_validated_alert_methods(data=data, validated=validated,
                run_environment=run_environment)

        if body_task_links is not None:
            updated_task_links = []

            next_rank = 0

            for body_task_link in body_task_links:
                rank = body_task_link.get('rank', next_rank)
                next_rank = rank + 1

                task_link = TaskLink(
                    name=body_task_link['name'],
                    link_url_template=body_task_link['link_url_template'],
                    description=body_task_link.get('description', ''),
                    icon_url=body_task_link.get('icon_url', ''),
                    rank=rank,
                    created_by_user=user,
                    created_by_group=group
                )
                updated_task_links.append(task_link)

            validated['task_links'] = updated_task_links

        validated['is_service'] = is_service

        if is_service is True:
            if min_service_instance_count and (min_service_instance_count < 0):
                raise serializers.ValidationError({
                    'min_service_instance_count': ['Must be greater than or equal to 0']
                })

            if schedule:
                raise serializers.ValidationError({
                    'schedule': ['Must be blank for services']
                })

            validated.schedule = ''
        elif is_service is False:
            validated['service_instance_count'] = None
            validated['min_service_instance_count'] = None

        return validated

    def to_representation(self, instance: Task) -> Any:
        obj = super().to_representation(instance)
        obj['links'] = LinkSerializer(instance=instance.tasklink_set,
                many=True).data
        return obj

    def create(self, validated_data):
        return self.create_or_update(None, validated_data)

    def update(self, instance, validated_data):
        return self.create_or_update(instance, validated_data)

    def create_or_update(self, instance, validated_data):
        #print(f"request = {self.context['request']}")
        #print(f"validated data = {validated_data}")

        user, _group = required_user_and_group_from_request()

        defaults = validated_data

        logger.info(f"Task create_or_update(), validated_data = {defaults}, {instance=}")

        if instance:
            uuid = instance.uuid
        else:
            uuid = defaults.pop('uuid', None)

        is_service = defaults.pop('is_service', None)
        service_instance_count = defaults.get('service_instance_count')
        min_service_instance_count = defaults.get('min_service_instance_count')

        is_service_defined = (is_service and service_instance_count) or (is_service is False)

        load_balancer_details_list = defaults.pop('aws_ecs_load_balancer_details_set', None)
        alert_methods = defaults.pop('alert_methods', None)

        task_links = defaults.pop('task_links', None)

        group = validated_data.get('created_by_group')

        if is_service_defined and (load_balancer_details_list is None):
            logger.info(f"Task update or create with {defaults}, {uuid=}")

            if not is_service:
                defaults['service_instance_count'] = None
                defaults['min_service_instance_count'] = None

            if uuid:
                task, _created = Task.objects.update_or_create(
                    uuid=uuid, created_by_group=group,
                    defaults=defaults)

                logger.info(f"Done Task update or create with {defaults}")
            else:
                name = defaults.pop('name')
                defaults['created_by_user'] = user
                task, _created = Task.objects.update_or_create(
                    name=name, created_by_group=group,
                    defaults=defaults)
        else:
            if instance:
                task = instance
            else:
                name = defaults['name']
                task = Task.objects.filter(name=name,
                        created_by_group=group).first()

            old_self = None
            if task is None:
                if is_service:
                    if service_instance_count is None:
                        defaults['service_instance_count'] = 1

                    if min_service_instance_count is None:
                        defaults['min_service_instance_count'] = 1
                else:
                    # If no service attributes were set until now, assume it's not a service
                    defaults['service_instance_count'] = None
                    defaults['min_service_instance_count'] = None

                task = Task(**defaults)
                task.should_skip_synchronize_with_run_environment = True

                if instance is None:
                    task.created_by_user = user

                task.save()
                self.update_aws_ecs_service_load_balancer_details_set(task,
                        load_balancer_details_list)
            else:
                old_self = copy.copy(task)
                old_self.id = None

                task.should_skip_synchronize_with_run_environment = True
                for attr, value in defaults.items():
                    setattr(task, attr, value)

                if is_service is None:
                    is_service = task.is_service

                if is_service:
                    task.schedule = ''

                    if (task.service_instance_count is None) and (defaults.get('service_instance_count') is None):
                        task.service_instance_count = 1

                    if (task.min_service_instance_count is None) and (defaults.get('min_service_instance_count') is None):
                        task.min_service_instance_count = 1
                else:
                    task.service_instance_count = None
                    task.min_service_instance_count = None
                    task.aws_ecs_service_load_balancer_health_check_grace_period_seconds = None

                task.save()
                if self.update_aws_ecs_service_load_balancer_details_set(
                        task, load_balancer_details_list):
                    task.aws_ecs_should_force_service_creation = True

            task.synchronize_with_run_environment(old_self=old_self)
            task.should_skip_synchronize_with_run_environment = False

        if alert_methods is not None:
            task.alert_methods.set(alert_methods)

        if task_links is not None:
            task.tasklink_set.all().delete()
            for task_link in task_links:
                task_link.task = task
                task_link.save()

        if not task.is_service:
            task.aws_ecs_service_load_balancer_details_set.all().delete()

        return task

    def execution_method_capability_serializer_for_type(self,
            method_name: str,
            task: Optional[Task] = None, is_service: Optional[bool] = None,
            run_environment: Optional[RunEnvironment] = None) \
            -> serializers.Serializer:
        #print(f"request = {self.context['request']}")
        request = self.context['request']
        omitted = (request.query_params.get('omit') or '').split(',')
        omit_details = 'execution_method_capability.details' in omitted

        if method_name == AwsEcsExecutionMethod.NAME:
            return AwsEcsExecutionMethodCapabilitySerializer(task,
                    required=False, is_service=is_service,
                    run_environment=run_environment,
                    omit_details=omit_details)

        return UnknownExecutionMethodCapabilitySerializer(task, required=False)

    def update_aws_ecs_service_load_balancer_details_set(self, task: Task,
            load_balancer_details_list: Optional[list[AwsEcsServiceLoadBalancerDetails]]):
        if load_balancer_details_list is None:
            return False

        must_recreate_service = False
        target_group_arn_to_lb = {}
        existing = task.aws_ecs_service_load_balancer_details_set.all()

        for details in existing:
            target_group_arn_to_lb[details.target_group_arn] = details

        for details in load_balancer_details_list:
            existing_details = target_group_arn_to_lb.pop(details.target_group_arn, None)

            if existing_details:
                if (existing_details.container_name != details.container_name) or \
                        (existing_details.container_port != details.container_port):
                    logger.info(f"Found different details for target group ARN: '{details.target_group_arn}': {details}")
                    must_recreate_service = True
                    existing_details.container_name = details.container_name
                    existing_details.container_port = details.container_port
                    existing_details.save()
            else:
                logger.info(f"Found new target group ARN: '{details.target_group_arn}', must recreate service")
                details.task = task
                details.save()
                must_recreate_service = True

        for details in target_group_arn_to_lb.values():
            logger.info(f"Found unused target group ARN: '{details.target_group_arn}', must recreate service")
            details.delete()
            must_recreate_service = True

        return must_recreate_service

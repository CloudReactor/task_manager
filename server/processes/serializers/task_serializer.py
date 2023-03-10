from typing import (
    Any, Mapping, Optional,
    Type, Union,
    cast
)

import copy
import logging

from rest_framework import serializers
from rest_framework.exceptions import (
    APIException, ErrorDetail, ValidationError
)

from rest_flex_fields.serializers import FlexFieldsSerializerMixin

from drf_spectacular.utils import (
    extend_schema_field,
    PolymorphicProxySerializer,
)

# Legacy
from .aws_ecs_execution_method_capability_serializer import (
    AwsEcsExecutionMethodCapabilitySerializer
)
from .generic_execution_method_capability_serializer import (
    GenericExecutionMethodCapabilitySerializer
)
from .unknown_execution_method_capability_serializer import (
    UnknownExecutionMethodCapabilitySerializer
)

# Stopgap
from .generic_execution_method_capability_stopgap_serializer import (
    GenericExecutionMethodCapabilityStopgapSerializer
)
from .aws_ecs_execution_method_capability_stopgap_serializer import (
    AwsEcsExecutionMethodCapabilityStopgapSerializer
)

from ..common.request_helpers import (
    ensure_group_access_level,
    required_user_and_group_from_request
)

from ..execution_methods import *
from ..execution_methods.aws_settings import INFRASTRUCTURE_TYPE_AWS
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
        source='aws_ecs_service_arn', allow_null=True)

    service_infrastructure_website_url = serializers.ReadOnlyField(
        source='aws_ecs_service_infrastructure_website_url',
        allow_null=True)

    service_arn_updated_at = serializers.DateTimeField(
        source='aws_ecs_service_updated_at', allow_null=True,
        read_only=True)

SUPPORTED_EXECUTION_METHODS = [
    AwsEcsExecutionMethod,
    AwsLambdaExecutionMethod,
    UnknownExecutionMethod,
]

UPPER_METHOD_TYPE_TO_EXECUTION_METHOD_NAME = {
    getattr(method, 'NAME').upper() :
        getattr(method, 'NAME') for method in SUPPORTED_EXECUTION_METHODS
}


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
        fields = [
            'uuid', 'name', 'url', 'description', 'dashboard_url',
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
            'max_postponed_failure_count', 'max_postponed_missing_execution_count',
            'max_postponed_timeout_count',
            'min_missing_execution_delay_seconds',
            'postponed_failure_before_success_seconds',
            'postponed_missing_execution_before_start_seconds',
            'postponed_timeout_before_success_seconds',
            'should_clear_failure_alerts_on_success',
            'should_clear_timeout_alerts_on_success',
            'project_url', 'log_query', 'logs_url',
            'links',
            'run_environment',
            'allocated_cpu_units',
            'allocated_memory_mb',
            'execution_method_capability', # Deprecated
            'execution_method_type',
            'execution_method_capability_details',
            'capabilities',
            'infrastructure_type', 'infrastructure_settings',
            'is_scheduling_managed', 'scheduling_provider_type',
            'scheduling_settings',
            'is_service_managed', 'service_provider_type', 'service_settings',
            'default_input_value', 'input_value_schema', 'output_value_schema',
            'managed_probability', 'failure_report_probability',
            'timeout_report_probability',
            'alert_methods',
            'other_metadata',
            'latest_task_execution',
            'current_service_info', # Deprecated
            'created_by_user', 'created_by_group',
            'was_auto_created', 'passive', 'enabled',
            'created_at', 'updated_at',
        ]

        read_only_fields = [
            'url', 'uuid',
            'is_service', 'capabilities',
            'latest_task_execution', 'current_service_info',
            'dashboard_url', 'infrastructure_website_url', 'logs_url',
            'created_at', 'updated_at',
        ]

    latest_task_execution = serializers.SerializerMethodField(
            allow_null=True)

    url = serializers.HyperlinkedIdentityField(
            view_name='tasks-detail',
            lookup_field='uuid')

    # Deprecated
    execution_method_capability = serializers.SerializerMethodField()

    # Deprecated
    current_service_info = serializers.SerializerMethodField(
            allow_null=True)

    capabilities = serializers.SerializerMethodField()

    alert_methods = NameAndUuidSerializer(
            include_name=True,
            view_name='alert_methods-detail',
            many=True, required=False)

    links = LinkSerializer(many=True, required=False)

    @extend_schema_field(TaskExecutionSerializer)
    def get_latest_task_execution(self, obj: Task):
        if obj.latest_task_execution is None:
            return None

        # Set the Task so we don't get N+1 queries looking back
        # Seems to slow down in ECS even though it stops N+1 queries
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
                method_name=method_name, task=obj, is_legacy_schema=True).data

    def get_capabilities(self, task: Task) -> list[str]:
        if task.passive:
            return []

        return [c.name for c in task.execution_method().capabilities()]

    # Deprecated
    @extend_schema_field(CurrentServiceInfoSerializer(required=False,
            read_only=True))
    def get_current_service_info(self, obj: Task):
        if not obj.is_service:
            return None

        if obj.execution_method_type == AwsEcsExecutionMethod.NAME:
            return CurrentServiceInfoSerializer(instance=obj,
                    context=self.context).data
        return None

    def validate(self, attrs: Mapping[str, Any]) -> Mapping[str, Any]:
        task: Optional[Task] = None
        if self.instance:
            task = cast(Task, self.instance)

        passive = attrs.get('passive')
        if (passive is None) and task:
            passive = task.passive

        if passive is None:
            passive = False

        execution_method_type = attrs.get('execution_method_type')

        # Legacy support
        if execution_method_type is None:
            legacy_emc = attrs.get('execution_method_capability')

            if legacy_emc:
                execution_method_type = legacy_emc.get('type')

        if not execution_method_type:
            execution_method_type = task.execution_method_type if task \
                else UnknownExecutionMethod.NAME

        if (not passive) and (execution_method_type == UnknownExecutionMethod.NAME):
            raise ValidationError({
                'passive': [ErrorDetail('Non-passive Tasks may not have an Unknown execution method',
                        code='invalid')]
            })

        return attrs

    def to_internal_value(self, data):
        body_task_links = data.pop('links', None) or \
            data.pop('process_type_links', None)

        legacy_emc = data.pop('execution_method_capability', None)
        logger.info(f"Removed {legacy_emc=}")

        validated = super().to_internal_value(data)

        request = self.context.get('request')
        user, group = required_user_and_group_from_request(request)

        task: Optional[Task] = cast(Task, self.instance) if self.instance else None

        run_environment = validated.get('run_environment',
            task.run_environment if task else None)

        if run_environment is None:
            raise ValidationError({
                'run_environment': ErrorDetail('Run Environment is required', 'missing')
            })

        # Ensure the API key has Developer access to the Run Environment
        # of the Task that will be updated.
        if task and (run_environment.pk != task.run_environment.pk):
            ensure_group_access_level(group=group,
                min_access_level=UserGroupAccessLevel.ACCESS_LEVEL_DEVELOPER,
                run_environment=task.run_environment,
                request=request)

        # Not sure why is_service isn't in validated even when specified in the
        # request body, falling back to original request.
        is_service = validated.pop('is_service', data.get('is_service'))
        service_instance_count = validated.get('service_instance_count')
        min_service_instance_count = validated.get('min_service_instance_count')
        schedule = validated.get('schedule')

        if (service_instance_count is not None) and (service_instance_count > 0):
            if is_service is False:
                raise serializers.ValidationError({
                    'service_instance_count': ['Must null for services']
                })
            is_service = True


        execution_method_dict = validated.get('execution_method_capability_details')

        # deprecated
        is_legacy_schema = (legacy_emc is not None) and \
            (execution_method_dict is None)
        logger.debug(f"{is_legacy_schema=}")

        execution_method_dict = execution_method_dict or legacy_emc

        logger.debug(f"{execution_method_dict=}")

        execution_method_type: Optional[str] = None

        if task:
            execution_method_type = task.execution_method_type

        if is_legacy_schema:
            execution_method_type = legacy_emc.get('type',
                    execution_method_type)

        execution_method_type = validated.get('execution_method_type',
            execution_method_type)

        if execution_method_type:
            known_execution_method_type = UPPER_METHOD_TYPE_TO_EXECUTION_METHOD_NAME.get(
                execution_method_type.upper())

            if known_execution_method_type:
                execution_method_type = known_execution_method_type
            else:
                logger.warning(f"Unsupported execution method type: '{execution_method_type}")
        else:
            execution_method_type = UnknownExecutionMethod.NAME

        if execution_method_type is None:
            raise APIException("TaskSerializer.to_internal_value() execution_method_type is None?")

        logger.debug(f"{execution_method_type=}")

        validated['execution_method_type'] = execution_method_type

        if execution_method_dict is not None:
            ems = self.execution_method_capability_serializer_for_type(
                    method_name=execution_method_type, task=task,
                    is_service=is_service, run_environment=run_environment,
                    is_legacy_schema=is_legacy_schema)

            em_validated = ems.to_internal_value(execution_method_dict)

            logger.debug(f"{em_validated=}")

            validated |= em_validated

            # Execution method serializer may set is_service if it was None
            if 'is_service' in validated:
                is_service = validated['is_service']

        infrastructure_type = validated.get('infrastructure_type')

        if infrastructure_type == INFRASTRUCTURE_TYPE_AWS:
            infrastructure_settings = data.get('infrastructure_settings')

            if infrastructure_settings:
                self.copy_props_with_prefix(dest_dict=validated,
                    src_dict=infrastructure_settings,
                    dest_prefix='aws_',
                    included_keys=['tags'])

                network_settings = infrastructure_settings.get('network')
                if network_settings:
                    self.copy_props_with_prefix(dest_dict=validated,
                        src_dict=network_settings,
                        dest_prefix='aws_default_',
                        included_keys=['subnets'])
                    self.copy_props_with_prefix(dest_dict=validated,
                        src_dict=network_settings,
                        dest_prefix='aws_ecs_default_',
                        included_keys=['security_groups', 'assign_public_ip'])

        if (is_service is None) and schedule:
            is_service = False

        if (is_service is None) and task:
            is_service = task.is_service

        if (min_service_instance_count is not None) \
                and (min_service_instance_count > 0):
            if is_service is False:
                raise serializers.ValidationError({
                    'min_service_instance_count': ['Must null for services']
                })

            is_service = True

        validated['is_service'] = is_service

        if is_service:
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

            if min_service_instance_count < 0:
                raise serializers.ValidationError({
                    'min_service_instance_count': ['Must be greater than or equal to 0']
                })

            if min_service_instance_count > service_instance_count:
                raise serializers.ValidationError({
                    'min_service_instance_count': ['Must be less than or equal to service_instance_count']
                })

            if schedule:
                raise serializers.ValidationError({
                    'schedule': ['Must be blank for services']
                })

            validated['schedule'] = ''
            validated['min_service_instance_count'] = min_service_instance_count
            validated['service_instance_count'] = service_instance_count

            if ('is_service_managed' not in validated) and \
                ((task is None) or (task.is_service_managed is None)):
                validated['is_service_managed'] = True
        else:
            if service_instance_count and (service_instance_count > 0):
                raise serializers.ValidationError({
                    'service_instance_count': ['Must be null or zero for non-services']
                })

            if min_service_instance_count and (min_service_instance_count > 0):
                raise serializers.ValidationError({
                    'min_service_instance_count': ['Must be non-positive if service_instance_count is negative']
                })

            if validated.get('is_service_managed'):
                raise serializers.ValidationError({
                    'is_service_managed': ['Cannot be true for non-services']
                })

            validated['service_instance_count'] = None
            validated['min_service_instance_count'] = None
            validated['is_service_managed'] = None

        if schedule:
            if ('is_scheduling_managed' not in validated) and \
                ((task is None) or (task.is_scheduling_managed is None)):
                validated['is_scheduling_managed'] = True

            if ('scheduled_instance_count' not in validated) and \
                ((task is None) or (task.scheduled_instance_count is None)):
                validated['scheduled_instance_count'] = 1
        else:
            if validated.get('is_scheduling_managed'):
                raise serializers.ValidationError({
                    'is_scheduling_managed': ['Cannot be true for unscheduled Tasks']
                })

            # TODO: allow this to be non-zero, in case scheduling settings set without schedule
            if validated.get('scheduled_instance_count'):
                raise serializers.ValidationError({
                    'scheduled_instance_count': ['Cannot be non-zero for unscheduled Tasks']
                })

            validated['scheduled_instance_count'] = None


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
        request = self.context['request']

        user, _group = required_user_and_group_from_request(request=request)

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
        task: Optional[Task] = None

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
                self.update_aws_ecs_service_load_balancer_details_set(
                        task, load_balancer_details_list)

            task.synchronize_with_run_environment(old_self=old_self, is_saving=True)
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
            run_environment: Optional[RunEnvironment] = None,
            is_legacy_schema: bool = False) \
            -> serializers.Serializer:
        #print(f"request = {self.context['request']}")
        request = self.context['request']
        omitted = (request.query_params.get('omit') or '').split(',')

        if is_legacy_schema:
            omit_details = 'execution_method_capability.details' in omitted

            if method_name == AwsEcsExecutionMethod.NAME:
                return AwsEcsExecutionMethodCapabilitySerializer(task,
                        required=False, is_service=is_service,
                        run_environment=run_environment,
                        omit_details=omit_details)
            elif method_name == UnknownExecutionMethod.NAME:
                return UnknownExecutionMethodCapabilitySerializer(task,
                        required=False)
            else:
                return GenericExecutionMethodCapabilitySerializer(task,
                        required=False)
        else:
            if method_name == AwsEcsExecutionMethod.NAME:
                return AwsEcsExecutionMethodCapabilityStopgapSerializer(task,
                        required=False,
                        run_environment=run_environment)

            return GenericExecutionMethodCapabilityStopgapSerializer(task,
                        required=False)

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
